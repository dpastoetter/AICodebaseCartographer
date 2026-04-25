"""Build the file-level import/dependency graph."""
from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import PurePosixPath

from ..models import DepEdge, DependencyGraph, DepNode
from ..parsers.treesitter import ParsedFile, ParsedImport
from ..walker import WalkResult

log = logging.getLogger(__name__)


def build(walk: WalkResult, parsed: list[ParsedFile]) -> DependencyGraph:
    by_path = {p.file.rel_path: p for p in parsed}
    nodes: list[DepNode] = []
    for p in parsed:
        nodes.append(
            DepNode(
                id=p.file.rel_path,
                label=PurePosixPath(p.file.rel_path).name,
                language=p.file.language,
                lines=p.file.lines,
                group=_group_for(p.file.rel_path),
            )
        )

    files_by_lang_module: dict[str, dict[str, str]] = {
        "python": _python_module_index(by_path),
    }

    edges: list[DepEdge] = []
    seen: set[tuple[str, str]] = set()

    for p in parsed:
        for imp in p.imports:
            target = _resolve_import(p, imp, by_path, files_by_lang_module)
            if target is None or target == p.file.rel_path:
                continue
            key = (p.file.rel_path, target)
            if key in seen:
                continue
            seen.add(key)
            edges.append(DepEdge(source=p.file.rel_path, target=target))

    return DependencyGraph(nodes=nodes, edges=edges)


def _group_for(rel_path: str) -> str:
    parts = rel_path.split("/")
    return parts[0] if len(parts) > 1 else "(root)"


def _python_module_index(by_path: dict[str, ParsedFile]) -> dict[str, str]:
    """Map fully-qualified Python module name -> file path."""
    index: dict[str, str] = {}
    for path in by_path:
        if not path.endswith(".py") and not path.endswith(".pyi"):
            continue
        without_ext = path.rsplit(".", 1)[0]
        parts = without_ext.split("/")
        if parts[-1] == "__init__":
            parts = parts[:-1]
        if not parts:
            continue
        # Try multiple roots: full path, and trimmed (drop common src layout).
        for trim in range(len(parts)):
            mod = ".".join(parts[trim:])
            if mod and mod not in index:
                index[mod] = path
    return index


def _resolve_import(
    src_file: ParsedFile,
    imp: ParsedImport,
    by_path: dict[str, ParsedFile],
    by_lang_module: dict[str, dict[str, str]],
) -> str | None:
    lang = src_file.file.language
    if lang == "python":
        return _resolve_python(src_file, imp, by_path, by_lang_module["python"])
    if lang in {"javascript", "typescript", "tsx"}:
        return _resolve_js(src_file, imp, by_path)
    return None


def _resolve_python(
    src_file: ParsedFile,
    imp: ParsedImport,
    by_path: dict[str, ParsedFile],
    by_module: dict[str, str],
) -> str | None:
    spec = imp.module.strip()
    if not spec:
        return None
    src_path = src_file.file.rel_path
    src_pkg = src_path.rsplit("/", 1)[0] if "/" in src_path else ""

    if spec.startswith("."):
        leading = len(spec) - len(spec.lstrip("."))
        rel_name = spec[leading:]
        parts = src_pkg.split("/") if src_pkg else []
        # `.` -> current package; `..` -> parent.
        up = max(0, leading - 1)
        if up > len(parts):
            return None
        base = parts[: len(parts) - up]
        target_parts = base + (rel_name.split(".") if rel_name else [])
        target_dotted = ".".join(target_parts)
        return _python_lookup(target_dotted, by_path, by_module)

    return _python_lookup(spec, by_path, by_module)


def _python_lookup(
    dotted: str, by_path: dict[str, ParsedFile], by_module: dict[str, str]
) -> str | None:
    if not dotted:
        return None
    candidate_paths = [
        dotted.replace(".", "/") + ".py",
        dotted.replace(".", "/") + "/__init__.py",
    ]
    for c in candidate_paths:
        if c in by_path:
            return c
    if dotted in by_module:
        return by_module[dotted]
    parent = dotted.rsplit(".", 1)[0]
    if parent in by_module:
        return by_module[parent]
    return None


_JS_EXTS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")


def _resolve_js(
    src_file: ParsedFile,
    imp: ParsedImport,
    by_path: dict[str, ParsedFile],
) -> str | None:
    spec = imp.module
    if not spec or not (spec.startswith(".") or spec.startswith("/")):
        return None
    src_dir = (
        src_file.file.rel_path.rsplit("/", 1)[0]
        if "/" in src_file.file.rel_path
        else ""
    )
    base = PurePosixPath(src_dir) / spec
    candidates = [str(base)]
    for ext in _JS_EXTS:
        candidates.append(f"{base}{ext}")
        candidates.append(f"{base}/index{ext}")
    for c in candidates:
        norm = _normalize(c)
        if norm in by_path:
            return norm
    return None


def _normalize(p: str) -> str:
    parts: list[str] = []
    for seg in p.split("/"):
        if seg in {"", "."}:
            continue
        if seg == "..":
            if parts:
                parts.pop()
            continue
        parts.append(seg)
    return "/".join(parts)


def fan_in_out(graph: DependencyGraph) -> tuple[dict[str, int], dict[str, int]]:
    fan_in: dict[str, int] = defaultdict(int)
    fan_out: dict[str, int] = defaultdict(int)
    for e in graph.edges:
        fan_out[e.source] += 1
        fan_in[e.target] += 1
    return fan_in, fan_out
