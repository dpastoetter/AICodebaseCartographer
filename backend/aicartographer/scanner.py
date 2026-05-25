"""Top-level scan orchestration.

Walks a project, parses each supported file, then runs the analysis pipeline
(dependency graph, symbol graph, hotspots, tech radar) and persists every
artifact under `~/.aicartographer/scans/<scan_id>/`.
"""
from __future__ import annotations

import asyncio
import json
import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .analysis import brief as brief_analysis
from .analysis import deps as deps_analysis
from .analysis import hotspots as hotspots_analysis
from .analysis import risks as risks_analysis
from .analysis import symbols as symbols_analysis
from .analysis import tech as tech_analysis
from .analysis import vulns as vulns_analysis
from .models import (
    ArchitectureBrief,
    DependencyGraph,
    Hotspots,
    LLMInfo,
    ModuleCard,
    RisksReport,
    ScanProgress,
    ScanRequest,
    ScanState,
    ScanStatus,
    ScanTotals,
    SymbolGraph,
    TechRadar,
    TreeResponse,
    VulnsReport,
)
from .parsers.treesitter import ParsedFile, parse_file
from .storage import scan_dir
from .walker import WalkResult, walk_project

log = logging.getLogger(__name__)


@dataclass
class ScanRecord:
    status: ScanStatus
    parsed: list[ParsedFile] = field(default_factory=list)
    walk: WalkResult | None = None
    cards: dict[str, ModuleCard] = field(default_factory=dict)
    listeners: list[asyncio.Queue] = field(default_factory=list)


class ScanRegistry:
    """In-memory registry of running and completed scans."""

    def __init__(self) -> None:
        self._records: dict[str, ScanRecord] = {}
        self._lock = threading.Lock()

    def create(self, request: ScanRequest) -> ScanRecord:
        scan_id = uuid.uuid4().hex[:12]
        status = ScanStatus(
            scan_id=scan_id,
            root_path=str(Path(request.path).expanduser().resolve()),
            state="queued",
            started_at=datetime.now(timezone.utc),
            llm=LLMInfo(kind=request.llm, model=request.model),
        )
        record = ScanRecord(status=status)
        with self._lock:
            self._records[scan_id] = record
        return record

    def get(self, scan_id: str) -> ScanRecord | None:
        with self._lock:
            return self._records.get(scan_id)

    def all(self) -> list[ScanStatus]:
        with self._lock:
            return [r.status for r in self._records.values()]

    def hydrate_from_disk(self) -> None:
        from .storage import scans_root

        root = scans_root()
        for d in root.iterdir():
            if not d.is_dir():
                continue
            status_file = d / "status.json"
            if not status_file.exists():
                continue
            try:
                data = json.loads(status_file.read_text())
                status = ScanStatus.model_validate(data)
                with self._lock:
                    if status.scan_id not in self._records:
                        self._records[status.scan_id] = ScanRecord(status=status)
            except Exception as exc:  # noqa: BLE001
                log.warning("Could not hydrate scan %s: %s", d.name, exc)


registry = ScanRegistry()


def _set_state(record: ScanRecord, state: ScanState, message: str = "") -> None:
    record.status.state = state
    record.status.progress.message = message
    _persist_status(record)
    _broadcast(record, {"type": "status", "status": record.status.model_dump(mode="json")})


def _persist_status(record: ScanRecord) -> None:
    d = scan_dir(record.status.scan_id)
    (d / "status.json").write_text(record.status.model_dump_json(indent=2))


def _persist(record: ScanRecord, name: str, data: object) -> None:
    d = scan_dir(record.status.scan_id)
    if hasattr(data, "model_dump_json"):
        (d / name).write_text(data.model_dump_json(indent=2))  # type: ignore[union-attr]
    else:
        (d / name).write_text(json.dumps(data, indent=2, default=str))


def _broadcast(record: ScanRecord, event: dict) -> None:
    dead: list[asyncio.Queue] = []
    for q in record.listeners:
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        record.listeners.remove(q)


def run_scan_sync(record: ScanRecord, request: ScanRequest) -> None:
    """Run static analysis synchronously. LLM cards are kicked off separately."""
    try:
        _set_state(record, "scanning", "Walking project")
        root = Path(record.status.root_path)
        walk = walk_project(root, max_files=request.max_files)
        record.walk = walk
        record.status.totals = ScanTotals(
            files=len(walk.files),
            dirs=walk.dir_count,
            languages=len({f.language for f in walk.files if f.language}),
        )
        record.status.progress = ScanProgress(
            files_seen=len(walk.files), files_parsed=0, message="Parsing files"
        )
        _persist(record, "tree.json", TreeResponse(root=walk.tree))
        _set_state(record, "analyzing", "Parsing files with tree-sitter")

        parsed: list[ParsedFile] = []
        for i, f in enumerate(walk.files, 1):
            try:
                pf = parse_file(root, f)
                if pf is not None:
                    parsed.append(pf)
            except Exception as exc:  # noqa: BLE001
                log.debug("Parse failed for %s: %s", f.rel_path, exc)
                record.status.totals.errors += 1
            if i % 25 == 0 or i == len(walk.files):
                record.status.progress.files_parsed = i
                _persist_status(record)
                _broadcast(
                    record,
                    {"type": "progress", "progress": record.status.progress.model_dump()},
                )
        record.parsed = parsed
        record.status.totals.lines = sum(p.file.lines for p in parsed)

        _set_state(record, "analyzing", "Building dependency graph")
        dep_graph = deps_analysis.build(walk, parsed)
        _persist(record, "dependencies.json", dep_graph)

        _set_state(record, "analyzing", "Building symbol graph")
        sym_graph = symbols_analysis.build(parsed)
        _persist(record, "symbols.json", sym_graph)

        _set_state(record, "analyzing", "Detecting tech")
        tech = tech_analysis.build(root, walk, parsed)
        _persist(record, "tech.json", tech)

        _set_state(record, "analyzing", "Computing hotspots")
        spots = hotspots_analysis.build(root, walk, parsed, dep_graph)
        _persist(record, "hotspots.json", spots)

        _set_state(record, "analyzing", "Computing risks")
        risks = risks_analysis.build(root, walk, parsed)
        _persist(record, "risks.json", risks)

        _set_state(record, "analyzing", "Querying dependency vulnerabilities (OSV)")
        vulns = vulns_analysis.build(root)
        _persist(record, "vulns.json", vulns)

        _set_state(record, "analyzing", "Building architecture brief")
        brief = brief_analysis.build(root, walk, tech, dep_graph, spots, risks, vulns)
        _persist(record, "brief.json", brief)

        record.status.finished_at = datetime.now(timezone.utc)
        _set_state(record, "done", "Static analysis complete")
    except Exception as exc:  # noqa: BLE001
        log.exception("Scan failed")
        record.status.error = str(exc)
        record.status.finished_at = datetime.now(timezone.utc)
        _set_state(record, "error", f"Scan failed: {exc}")


def load_artifact(scan_id: str, name: str):
    d = scan_dir(scan_id)
    p = d / name
    if not p.exists():
        return None
    return json.loads(p.read_text())


__all__ = [
    "DependencyGraph",
    "Hotspots",
    "ArchitectureBrief",
    "RisksReport",
    "VulnsReport",
    "ScanRecord",
    "ScanRegistry",
    "SymbolGraph",
    "TechRadar",
    "TreeResponse",
    "load_artifact",
    "registry",
    "run_scan_sync",
]
