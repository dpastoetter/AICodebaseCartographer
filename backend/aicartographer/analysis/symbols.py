"""Build the symbol graph: classes / functions / methods and best-effort calls."""
from __future__ import annotations

from collections import defaultdict

from ..models import Symbol, SymbolEdge, SymbolGraph, SymbolKind
from ..parsers.treesitter import ParsedFile

# Cap edges so very large repos do not produce a 50k-edge graph the UI can't render.
MAX_EDGES = 4000


def _kind_to_model(kind: str) -> SymbolKind:
    if kind in {"class", "function", "method", "interface", "type"}:
        return kind  # type: ignore[return-value]
    return "function"


def build(parsed: list[ParsedFile]) -> SymbolGraph:
    nodes: list[Symbol] = []
    by_name: dict[str, list[Symbol]] = defaultdict(list)
    file_symbols: dict[str, list[Symbol]] = defaultdict(list)

    for p in parsed:
        for sym in p.symbols:
            sid = _symbol_id(p.file.rel_path, sym.name, sym.parent)
            node = Symbol(
                id=sid,
                name=sym.name,
                kind=_kind_to_model(sym.kind),
                file=p.file.rel_path,
                line=sym.line,
                parent=sym.parent,
            )
            nodes.append(node)
            by_name[sym.name].append(node)
            file_symbols[p.file.rel_path].append(node)

    edges: list[SymbolEdge] = []
    seen: set[tuple[str, str]] = set()

    for p in parsed:
        callers = file_symbols.get(p.file.rel_path, [])
        for call in p.calls:
            if not call.caller:
                continue
            caller_id = _resolve_caller(p.file.rel_path, call.caller, callers)
            if caller_id is None:
                continue
            targets = by_name.get(call.name, [])
            if not targets:
                continue
            target = _pick_target(p.file.rel_path, targets)
            if target.id == caller_id:
                continue
            key = (caller_id, target.id)
            if key in seen:
                continue
            seen.add(key)
            edges.append(SymbolEdge(source=caller_id, target=target.id))
            if len(edges) >= MAX_EDGES:
                break
        if len(edges) >= MAX_EDGES:
            break

    return SymbolGraph(nodes=nodes, edges=edges)


def _symbol_id(file: str, name: str, parent: str | None) -> str:
    if parent:
        return f"{file}::{parent}.{name}"
    return f"{file}::{name}"


def _resolve_caller(
    file: str, caller_name: str, file_syms: list[Symbol]
) -> str | None:
    for s in file_syms:
        if caller_name == s.name and s.parent is None:
            return s.id
        if s.parent and caller_name == f"{s.parent}.{s.name}":
            return s.id
    return None


def _pick_target(source_file: str, candidates: list[Symbol]) -> Symbol:
    """Prefer targets in the same file; otherwise pick deterministically."""
    same_file = [c for c in candidates if c.file == source_file]
    if same_file:
        return same_file[0]
    return min(candidates, key=lambda s: (s.file, s.line))
