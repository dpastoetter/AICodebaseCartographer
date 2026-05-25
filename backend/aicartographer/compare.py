"""Diff two completed scans by comparing persisted artifacts."""
from __future__ import annotations

from typing import Any

from .models import ScanCompareResult
from .scanner import load_artifact


def _file_paths(tree: dict[str, Any] | None) -> set[str]:
    if not tree:
        return set()

    out: set[str] = set()

    def walk(node: dict[str, Any]) -> None:
        if not node.get("is_dir"):
            out.add(str(node.get("path", "")))
        for c in node.get("children") or []:
            if isinstance(c, dict):
                walk(c)

    root = tree.get("root")
    if isinstance(root, dict):
        walk(root)
    return {p for p in out if p}


def _edge_set(deps: dict[str, Any] | None) -> set[tuple[str, str]]:
    if not deps:
        return set()
    edges = deps.get("edges") or []
    out: set[tuple[str, str]] = set()
    for e in edges:
        if isinstance(e, dict):
            out.add((str(e.get("source", "")), str(e.get("target", ""))))
    return out


def _risk_ids(risks: dict[str, Any] | None) -> set[str]:
    if not risks:
        return set()
    return {str(f.get("id", "")) for f in (risks.get("findings") or []) if f.get("id")}


def _vuln_keys(vulns: dict[str, Any] | None) -> set[str]:
    if not vulns:
        return set()
    keys: set[str] = set()
    for pkg in vulns.get("packages") or []:
        if not isinstance(pkg, dict):
            continue
        name = pkg.get("name", "")
        version = pkg.get("version", "")
        for v in pkg.get("vulnerabilities") or []:
            if isinstance(v, dict) and v.get("vuln_id"):
                keys.add(f"{name}@{version}:{v['vuln_id']}")
    return keys


def _hotspot_map(hotspots: dict[str, Any] | None) -> dict[str, int]:
    if not hotspots:
        return {}
    out: dict[str, int] = {}
    for key in ("largest", "most_imported", "most_complex", "churn"):
        for entry in hotspots.get(key) or []:
            if isinstance(entry, dict) and entry.get("path"):
                path = str(entry["path"])
                out[path] = max(out.get(path, 0), int(entry.get("lines") or 0))
    return out


def compare_scans(scan_a: str, scan_b: str) -> ScanCompareResult:
    tree_a = load_artifact(scan_a, "tree.json")
    tree_b = load_artifact(scan_b, "tree.json")
    paths_a = _file_paths(tree_a)
    paths_b = _file_paths(tree_b)

    deps_a = load_artifact(scan_a, "dependencies.json")
    deps_b = load_artifact(scan_b, "dependencies.json")
    edges_a = _edge_set(deps_a)
    edges_b = _edge_set(deps_b)

    risks_a = load_artifact(scan_a, "risks.json")
    risks_b = load_artifact(scan_b, "risks.json")
    rid_a = _risk_ids(risks_a)
    rid_b = _risk_ids(risks_b)

    vulns_a = load_artifact(scan_a, "vulns.json")
    vulns_b = load_artifact(scan_b, "vulns.json")
    vk_a = _vuln_keys(vulns_a)
    vk_b = _vuln_keys(vulns_b)

    hs_a = _hotspot_map(load_artifact(scan_a, "hotspots.json"))
    hs_b = _hotspot_map(load_artifact(scan_b, "hotspots.json"))

    line_deltas: list[dict[str, int | str]] = []
    for path in sorted(paths_a & paths_b):
        la = hs_a.get(path, 0)
        lb = hs_b.get(path, 0)
        if la != lb:
            line_deltas.append({"path": path, "lines_a": la, "lines_b": lb, "delta": lb - la})

    return ScanCompareResult(
        scan_a=scan_a,
        scan_b=scan_b,
        files_added=sorted(paths_b - paths_a),
        files_removed=sorted(paths_a - paths_b),
        deps_added=sorted(f"{s} -> {t}" for s, t in edges_b - edges_a),
        deps_removed=sorted(f"{s} -> {t}" for s, t in edges_a - edges_b),
        risks_added=sorted(rid_b - rid_a),
        risks_removed=sorted(rid_a - rid_b),
        vulns_added=sorted(vk_b - vk_a),
        vulns_removed=sorted(vk_a - vk_b),
        line_deltas=line_deltas[:100],
    )
