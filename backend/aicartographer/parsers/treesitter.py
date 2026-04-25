"""Tree-sitter based parser for Python, JavaScript, TypeScript, and TSX.

Extracts:
- imports (raw spec string)
- top-level and nested symbols (class, function, method)
- best-effort call references

The implementation is deliberately conservative: when a grammar / query fails
we return whatever we managed to extract instead of erroring out the whole scan.
"""
from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

from tree_sitter import Language, Node, Parser, Query, QueryCursor

from ..walker import WalkedFile

log = logging.getLogger(__name__)


@dataclass
class ParsedSymbol:
    name: str
    kind: str
    line: int
    parent: str | None = None


@dataclass
class ParsedImport:
    raw: str
    module: str
    is_relative: bool = False


@dataclass
class ParsedCall:
    name: str
    line: int
    caller: str | None = None


@dataclass
class ParsedFile:
    file: WalkedFile
    imports: list[ParsedImport] = field(default_factory=list)
    symbols: list[ParsedSymbol] = field(default_factory=list)
    calls: list[ParsedCall] = field(default_factory=list)


_LANGUAGE_LOADERS = {
    "python": ("tree_sitter_python", "language"),
    "javascript": ("tree_sitter_javascript", "language"),
    "tsx": ("tree_sitter_typescript", "language_tsx"),
    "typescript": ("tree_sitter_typescript", "language_typescript"),
}


@cache
def _language_for(lang: str) -> Language | None:
    spec = _LANGUAGE_LOADERS.get(lang)
    if not spec:
        return None
    module_name, fn_name = spec
    try:
        mod = __import__(module_name)
    except ImportError:
        return None
    try:
        fn = getattr(mod, fn_name)
        return Language(fn())
    except Exception as exc:  # noqa: BLE001
        log.warning("Failed to load grammar for %s: %s", lang, exc)
        return None


@cache
def _parser_for(lang: str) -> Parser | None:
    language = _language_for(lang)
    if language is None:
        return None
    return Parser(language)


@cache
def _query_for(lang: str, query_src: str) -> Query | None:
    language = _language_for(lang)
    if language is None:
        return None
    try:
        return Query(language, query_src)
    except Exception as exc:  # noqa: BLE001
        log.warning("Bad query for %s: %s", lang, exc)
        return None


def _text(node: Node, src: bytes) -> str:
    return src[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def _strip_quotes(s: str) -> str:
    s = s.strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    if s.startswith("`") and s.endswith("`"):
        return s[1:-1]
    return s


# Imports queries (raw module strings).
_IMPORT_QUERIES = {
    "python": """
        (import_statement name: (dotted_name) @import)
        (import_statement name: (aliased_import name: (dotted_name) @import))
        (import_from_statement module_name: (dotted_name) @import)
        (import_from_statement module_name: (relative_import) @import.relative)
    """,
    "javascript": """
        (import_statement source: (string) @import)
        (call_expression
          function: (identifier) @_fn
          arguments: (arguments (string) @import)
          (#match? @_fn "^(require|import)$"))
    """,
    "typescript": """
        (import_statement source: (string) @import)
        (call_expression
          function: (identifier) @_fn
          arguments: (arguments (string) @import)
          (#match? @_fn "^(require|import)$"))
    """,
    "tsx": """
        (import_statement source: (string) @import)
        (call_expression
          function: (identifier) @_fn
          arguments: (arguments (string) @import)
          (#match? @_fn "^(require|import)$"))
    """,
}


def _collect_imports(lang: str, root: Node, src: bytes) -> list[ParsedImport]:
    q = _query_for(lang, _IMPORT_QUERIES[lang])
    if q is None:
        return []
    cursor = QueryCursor(q)
    captures = cursor.captures(root)
    imports: list[ParsedImport] = []

    for cap_name, nodes in captures.items():
        if not cap_name.startswith("import"):
            continue
        is_relative = cap_name == "import.relative"
        for node in nodes:
            raw = _text(node, src)
            module = _strip_quotes(raw)
            if not module:
                continue
            if module.startswith("."):
                is_relative = True
            imports.append(ParsedImport(raw=raw, module=module, is_relative=is_relative))
    return imports


# Symbol container node types per language. Walking handles nesting + parent.
_SYMBOL_KINDS = {
    "python": {
        "class_definition": "class",
        "function_definition": "function",
    },
    "javascript": {
        "class_declaration": "class",
        "function_declaration": "function",
        "method_definition": "method",
        "lexical_declaration": None,
    },
    "typescript": {
        "class_declaration": "class",
        "function_declaration": "function",
        "method_definition": "method",
        "interface_declaration": "interface",
        "type_alias_declaration": "type",
        "enum_declaration": "type",
    },
    "tsx": {
        "class_declaration": "class",
        "function_declaration": "function",
        "method_definition": "method",
        "interface_declaration": "interface",
        "type_alias_declaration": "type",
        "enum_declaration": "type",
    },
}


def _name_of(node: Node, src: bytes) -> str | None:
    name_node = node.child_by_field_name("name")
    if name_node is not None:
        return _text(name_node, src)
    for child in node.children:
        if child.type in {"identifier", "type_identifier", "property_identifier"}:
            return _text(child, src)
    return None


def _walk_symbols(
    lang: str, root: Node, src: bytes
) -> tuple[list[ParsedSymbol], list[ParsedCall]]:
    kinds = _SYMBOL_KINDS.get(lang, {})
    symbols: list[ParsedSymbol] = []
    calls: list[ParsedCall] = []

    class_kinds = {"class", "interface"}

    def visit(node: Node, parent_class: str | None, enclosing: str | None) -> None:
        kind = kinds.get(node.type)
        new_enclosing = enclosing
        new_parent_class = parent_class

        if kind:
            name = _name_of(node, src)
            if name:
                # Methods inside a class definition.
                effective_kind = kind
                if kind == "function" and parent_class is not None and lang == "python":
                    effective_kind = "method"
                symbols.append(
                    ParsedSymbol(
                        name=name,
                        kind=effective_kind,
                        line=node.start_point[0] + 1,
                        parent=parent_class,
                    )
                )
                if effective_kind in class_kinds:
                    new_parent_class = name
                    new_enclosing = name
                else:
                    new_enclosing = (
                        f"{parent_class}.{name}" if parent_class else name
                    )

        if node.type in {"call", "call_expression"}:
            fn_node = node.child_by_field_name("function") or (
                node.children[0] if node.children else None
            )
            call_name = _call_target_name(fn_node, src)
            if call_name:
                calls.append(
                    ParsedCall(
                        name=call_name,
                        line=node.start_point[0] + 1,
                        caller=enclosing,
                    )
                )

        # Descend.
        for child in node.children:
            visit(child, new_parent_class, new_enclosing)

    visit(root, None, None)
    return symbols, calls


def _call_target_name(node: Node | None, src: bytes) -> str | None:
    if node is None:
        return None
    if node.type == "identifier":
        return _text(node, src)
    if node.type in {"attribute", "member_expression"}:
        prop = node.child_by_field_name("attribute") or node.child_by_field_name(
            "property"
        )
        if prop is not None:
            return _text(prop, src)
    return None


def parse_file(root: Path, walked: WalkedFile) -> ParsedFile | None:
    """Parse `walked` and return imports/symbols/calls. Returns None if no grammar."""
    lang = walked.language
    if lang not in _LANGUAGE_LOADERS:
        return ParsedFile(file=walked)
    parser = _parser_for(lang)
    if parser is None:
        return ParsedFile(file=walked)
    try:
        src = walked.abs_path.read_bytes()
    except OSError:
        return None

    try:
        tree = parser.parse(src)
    except Exception as exc:  # noqa: BLE001
        log.debug("parse failed for %s: %s", walked.rel_path, exc)
        return ParsedFile(file=walked)

    root_node = tree.root_node
    imports = _collect_imports(lang, root_node, src)
    symbols, calls = _walk_symbols(lang, root_node, src)
    return ParsedFile(
        file=walked, imports=imports, symbols=symbols, calls=calls
    )


__all__ = [
    "ParsedCall",
    "ParsedFile",
    "ParsedImport",
    "ParsedSymbol",
    "parse_file",
]


def supported_languages() -> Iterable[str]:
    return _LANGUAGE_LOADERS.keys()
