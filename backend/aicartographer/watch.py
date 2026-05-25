"""Living scan: watch filesystem and incrementally refresh artifacts."""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from .analysis import brief as brief_analysis
from .analysis import deps as deps_analysis
from .analysis import hotspots as hotspots_analysis
from .analysis import risks as risks_analysis
from .analysis import symbols as symbols_analysis
from .analysis import tech as tech_analysis
from .analysis import vulns as vulns_analysis
from .models import WatchStatus
from .parsers.treesitter import ParsedFile, parse_file
from .scanner import ScanRecord, _broadcast, _persist, registry

log = logging.getLogger(__name__)

DEBOUNCE_S = 2.0

_watchers: dict[str, _WatchSession] = {}
_lock = threading.Lock()


class _WatchSession:
    def __init__(self, scan_id: str, record: ScanRecord) -> None:
        self.scan_id = scan_id
        self.record = record
        self.enabled = True
        self.updating = False
        self.last_update: datetime | None = None
        self.message = ""
        self._stop = threading.Event()
        self._pending: set[str] = set()
        self._pending_lock = threading.Lock()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def status(self) -> WatchStatus:
        return WatchStatus(
            enabled=self.enabled,
            updating=self.updating,
            last_update=self.last_update,
            message=self.message,
        )

    def stop(self) -> None:
        self.enabled = False
        self._stop.set()

    def queue(self, rel_path: str) -> None:
        with self._pending_lock:
            self._pending.add(rel_path)

    def _loop(self) -> None:
        while not self._stop.is_set():
            time.sleep(0.4)
            if not self.enabled:
                continue
            with self._pending_lock:
                batch = list(self._pending)
                self._pending.clear()
            if not batch:
                continue
            deadline = time.time() + DEBOUNCE_S
            while time.time() < deadline and not self._stop.is_set():
                time.sleep(0.2)
                with self._pending_lock:
                    batch.extend(self._pending)
                    self._pending.clear()
            try:
                self.updating = True
                self.message = f"Updating {len(batch)} file(s)…"
                run_incremental_sync(self.record, batch)
                self.last_update = datetime.now(timezone.utc)
                self.message = "Up to date"
                _broadcast(
                    self.record,
                    {"type": "artifacts", "artifacts": ["dependencies", "symbols", "hotspots", "risks", "brief"]},
                )
            except Exception as exc:  # noqa: BLE001
                log.exception("Incremental update failed")
                self.message = f"Update failed: {exc}"
            finally:
                self.updating = False


def start_watch(scan_id: str) -> WatchStatus:
    record = registry.get(scan_id)
    if not record:
        raise ValueError("Scan not found")
    if record.status.state != "done":
        raise ValueError("Scan must be complete before watch mode")
    with _lock:
        existing = _watchers.get(scan_id)
        if existing:
            existing.enabled = True
            return existing.status()
        session = _WatchSession(scan_id, record)
        _watchers[scan_id] = session
    root = Path(record.status.root_path)
    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
    except ImportError as exc:
        raise RuntimeError("Install watchdog: pip install aicartographer[watch]") from exc

    class Handler(FileSystemEventHandler):
        def on_modified(self, event):  # noqa: N802
            if event.is_directory:
                return
            _on_file_event(scan_id, Path(event.src_path), root)

        def on_created(self, event):  # noqa: N802
            if not event.is_directory:
                _on_file_event(scan_id, Path(event.src_path), root)

        def on_deleted(self, event):  # noqa: N802
            if not event.is_directory:
                _on_file_event(scan_id, Path(event.src_path), root)

    observer = Observer()
    observer.schedule(Handler(), str(root), recursive=True)
    observer.daemon = True
    observer.start()
    session = _watchers[scan_id]
    session._observer = observer  # type: ignore[attr-defined]
    return session.status()


def stop_watch(scan_id: str) -> WatchStatus:
    with _lock:
        session = _watchers.pop(scan_id, None)
    if session:
        session.stop()
        obs = getattr(session, "_observer", None)
        if obs:
            obs.stop()
            obs.join(timeout=2)
        return WatchStatus(enabled=False, updating=False, message="Watch stopped")
    return WatchStatus(enabled=False, message="Watch not active")


def get_watch_status(scan_id: str) -> WatchStatus:
    with _lock:
        session = _watchers.get(scan_id)
    if session:
        return session.status()
    return WatchStatus(enabled=False)


def _on_file_event(scan_id: str, path: Path, root: Path) -> None:
    try:
        rel = path.relative_to(root).as_posix()
    except ValueError:
        return
    with _lock:
        session = _watchers.get(scan_id)
    if session and session.enabled:
        session.queue(rel)


def run_incremental_sync(record: ScanRecord, changed_paths: list[str]) -> None:
    root = Path(record.status.root_path)
    walk = record.walk
    if walk is None:
        raise RuntimeError("Scan walk data missing; run a full scan first")

    parsed_by_path = {p.file.rel_path: p for p in record.parsed}
    walk_paths = {f.rel_path for f in walk.files}

    for rel in changed_paths:
        full = root / rel
        if not full.exists():
            parsed_by_path.pop(rel, None)
            continue
        if rel not in walk_paths:
            continue
        wf = next((f for f in walk.files if f.rel_path == rel), None)
        if wf is None:
            continue
        try:
            pf = parse_file(root, wf)
            if pf is not None:
                parsed_by_path[rel] = pf
            else:
                parsed_by_path.pop(rel, None)
        except Exception as exc:  # noqa: BLE001
            log.debug("Incremental parse failed %s: %s", rel, exc)

    record.parsed = list(parsed_by_path.values())
    parsed: list[ParsedFile] = record.parsed

    dep_graph = deps_analysis.build(walk, parsed)
    _persist(record, "dependencies.json", dep_graph)

    sym_graph = symbols_analysis.build(parsed)
    _persist(record, "symbols.json", sym_graph)

    tech = tech_analysis.build(root, walk, parsed)
    _persist(record, "tech.json", tech)

    spots = hotspots_analysis.build(root, walk, parsed, dep_graph)
    _persist(record, "hotspots.json", spots)

    risks = risks_analysis.build(root, walk, parsed)
    _persist(record, "risks.json", risks)

    vulns = vulns_analysis.build(root)
    _persist(record, "vulns.json", vulns)

    brief = brief_analysis.build(root, walk, tech, dep_graph, spots, risks, vulns)
    _persist(record, "brief.json", brief)
