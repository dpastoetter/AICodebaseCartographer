"""Build a searchable index from scan artifacts (shared by Ask and MCP)."""
from __future__ import annotations

from typing import Any

from .scanner import load_artifact


def search_codebase(scan_id: str, query: str, *, limit: int = 25) -> list[dict[str, Any]]:
    q = query.strip().lower()
    if not q:
        return []

    items: list[dict[str, Any]] = []

    tree = load_artifact(scan_id, "tree.json")
    if tree:
        for path in _walk_paths(tree):
            name = path.split("/")[-1]
            items.append(
                {
                    "kind": "file",
                    "label": name,
                    "path": path,
                    "view": "mindmap",
                    "haystack": f"{name} {path}".lower(),
                }
            )

    symbols = load_artifact(scan_id, "symbols.json")
    if symbols:
        for s in symbols.get("nodes") or []:
            if not isinstance(s, dict):
                continue
            items.append(
                {
                    "kind": "symbol",
                    "label": s.get("name", ""),
                    "path": s.get("file"),
                    "line": s.get("line"),
                    "view": "symbols",
                    "haystack": f"{s.get('name')} {s.get('kind')} {s.get('file')}".lower(),
                }
            )

    risks = load_artifact(scan_id, "risks.json")
    if risks:
        for f in risks.get("findings") or []:
            if not isinstance(f, dict):
                continue
            items.append(
                {
                    "kind": "risk",
                    "label": f.get("title", ""),
                    "path": f.get("path"),
                    "line": f.get("line"),
                    "view": "risks",
                    "haystack": f"{f.get('title')} {f.get('path')} {f.get('rule')}".lower(),
                }
            )

    vulns = load_artifact(scan_id, "vulns.json")
    if vulns:
        for pkg in vulns.get("packages") or []:
            if not isinstance(pkg, dict):
                continue
            for v in pkg.get("vulnerabilities") or []:
                if not isinstance(v, dict):
                    continue
                label = f"{pkg.get('name')} — {v.get('vuln_id')}"
                items.append(
                    {
                        "kind": "vuln",
                        "label": label,
                        "path": None,
                        "view": "risks",
                        "haystack": f"{label} {v.get('summary')}".lower(),
                    }
                )

    cards = load_artifact(scan_id, "cards.json")
    if cards:
        for c in cards.get("cards") or []:
            if not isinstance(c, dict) or not c.get("summary"):
                continue
            path = c.get("path", "")
            items.append(
                {
                    "kind": "card",
                    "label": path.split("/")[-1],
                    "path": path,
                    "view": "cards",
                    "haystack": f"{path} {c.get('summary')}".lower(),
                }
            )

    scored: list[tuple[int, dict[str, Any]]] = []
    for it in items:
        hay = it.get("haystack", "")
        idx = hay.find(q)
        if idx < 0:
            continue
        score = 0 if idx == 0 else 1 + idx
        scored.append((score, it))

    scored.sort(key=lambda x: (x[0], str(x[1].get("label", ""))))
    out = []
    for _, it in scored[:limit]:
        row = {k: v for k, v in it.items() if k != "haystack"}
        out.append(row)
    return out


def _walk_paths(tree: dict[str, Any]) -> list[str]:
    out: list[str] = []

    def walk(node: dict[str, Any]) -> None:
        if not node.get("is_dir"):
            out.append(str(node.get("path", "")))
        for c in node.get("children") or []:
            if isinstance(c, dict):
                walk(c)

    root = tree.get("root")
    if isinstance(root, dict):
        walk(root)
    return [p for p in out if p]
