"""Hotspots: largest, most-imported, most-complex, recently changed files."""
from __future__ import annotations

import logging
import subprocess
from collections import Counter
from pathlib import Path

from ..models import DependencyGraph, HotspotEntry, Hotspots
from ..parsers.treesitter import ParsedFile
from ..walker import WalkResult
from .deps import fan_in_out

log = logging.getLogger(__name__)

TOP_N = 20


def build(
    root: Path, walk: WalkResult, parsed: list[ParsedFile], deps: DependencyGraph
) -> Hotspots:
    fan_in, fan_out = fan_in_out(deps)
    by_path = {p.file.rel_path: p for p in parsed}

    entries: dict[str, HotspotEntry] = {}
    for f in walk.files:
        entries[f.rel_path] = HotspotEntry(
            path=f.rel_path,
            lines=f.lines,
            fan_in=fan_in.get(f.rel_path, 0),
            fan_out=fan_out.get(f.rel_path, 0),
            complexity=_complexity_score(by_path.get(f.rel_path)),
        )

    churn = _git_churn(root, list(entries))
    if churn:
        for path, n in churn.items():
            if path in entries:
                entries[path].churn = n

    largest = sorted(entries.values(), key=lambda e: e.lines, reverse=True)[:TOP_N]
    most_imported = sorted(
        entries.values(), key=lambda e: e.fan_in, reverse=True
    )[:TOP_N]
    most_imported = [e for e in most_imported if e.fan_in > 0]
    most_complex = sorted(
        entries.values(), key=lambda e: e.complexity, reverse=True
    )[:TOP_N]
    most_complex = [e for e in most_complex if e.complexity > 0]
    churn_top: list[HotspotEntry] = []
    if churn:
        churn_top = sorted(
            entries.values(), key=lambda e: e.churn or 0, reverse=True
        )[:TOP_N]
        churn_top = [e for e in churn_top if (e.churn or 0) > 0]

    return Hotspots(
        largest=largest,
        most_imported=most_imported,
        most_complex=most_complex,
        churn=churn_top,
    )


def _complexity_score(p: ParsedFile | None) -> int:
    if p is None:
        return 0
    score = len(p.symbols) + len(p.calls) // 4
    return score


def _git_churn(root: Path, paths: list[str]) -> dict[str, int]:
    if not (root / ".git").exists():
        return {}
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "log", "--since=1.year.ago", "--name-only", "--pretty=format:"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (FileNotFoundError, subprocess.SubprocessError) as exc:
        log.debug("git churn unavailable: %s", exc)
        return {}
    if result.returncode != 0:
        return {}
    counter: Counter[str] = Counter()
    valid = set(paths)
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        if line in valid:
            counter[line] += 1
    return dict(counter)
