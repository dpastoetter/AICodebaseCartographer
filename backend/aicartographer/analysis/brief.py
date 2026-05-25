"""Deterministic repo-level architecture brief from scan artifacts."""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from ..models import (
    ArchitectureBrief,
    DependencyGraph,
    Hotspots,
    RisksReport,
    TechRadar,
    VulnsReport,
)
from ..walker import WalkResult


def build(
    root: Path,
    walk: WalkResult,
    tech: TechRadar,
    deps: DependencyGraph,
    hotspots: Hotspots,
    risks: RisksReport,
    vulns: VulnsReport,
) -> ArchitectureBrief:
    name = root.name
    langs = ", ".join(
        f"{lang.name} ({lang.lines} lines)" for lang in tech.languages[:5]
    )
    if not langs:
        langs = "unknown"

    frameworks = [i.name for i in tech.items if i.kind == "framework"][:8]
    tech_line = ", ".join(frameworks) if frameworks else "See Technology view for detected libraries."

    top_dirs = _top_level_dirs(walk)
    modules_line = ", ".join(top_dirs[:8]) if top_dirs else "(flat or single-package layout)"

    fan_in: Counter[str] = Counter()
    for e in deps.edges:
        fan_in[e.target] += 1
    hub = fan_in.most_common(3)
    hub_line = (
        ", ".join(f"{p} ({n} imports)" for p, n in hub) if hub else "No import edges detected yet."
    )

    largest = hotspots.largest[0].path if hotspots.largest else None
    hot_line = f"Largest file: {largest}." if largest else ""

    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "unknown": 4}
    top_risks = sorted(risks.findings, key=lambda f: sev_order.get(f.severity, 9))[:3]
    top_vuln_rows: list[str] = []
    for pkg in vulns.packages:
        for v in pkg.vulnerabilities:
            top_vuln_rows.append((pkg.name, v.vuln_id, v.severity))
    top_vuln_rows.sort(key=lambda x: sev_order.get(x[2], 9))
    top_vulns = [f"{n}: {vid} ({sev})" for n, vid, sev in top_vuln_rows[:3]]

    purpose = (
        f"{name} contains {len(walk.files)} source files across {len(tech.languages)} languages. "
        f"Primary languages: {langs}. "
        f"Top-level areas: {modules_line}."
    )

    return ArchitectureBrief(
        project_name=name,
        purpose=purpose,
        modules=modules_line,
        tech_stack=tech_line,
        dependency_hubs=hub_line,
        hotspots_note=hot_line,
        top_risks=[f.title + (f" ({f.path})" if f.path else "") for f in top_risks],
        top_vulns=top_vulns,
    )


def _top_level_dirs(walk: WalkResult) -> list[str]:
    dirs: Counter[str] = Counter()
    for f in walk.files:
        parts = f.rel_path.split("/")
        if len(parts) > 1:
            dirs[parts[0]] += 1
    return [d for d, _ in dirs.most_common()]
