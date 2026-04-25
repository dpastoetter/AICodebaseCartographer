"""Walk a project directory, honoring .gitignore and skipping noise."""
from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass, field
from pathlib import Path

import pathspec

from .models import FileNode

log = logging.getLogger(__name__)

# Folders we never want to descend into, even without a .gitignore.
DEFAULT_IGNORE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    "dist",
    "build",
    "out",
    "target",
    ".next",
    ".nuxt",
    ".turbo",
    ".cache",
    ".idea",
    ".vscode",
    ".gradle",
    ".aicartographer",
}

DEFAULT_IGNORE_GLOBS = [
    "*.lock",
    "*.lockb",
    "*.min.js",
    "*.min.css",
    "*.map",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "uv.lock",
    "Cargo.lock",
    "go.sum",
]

# Map extensions to a normalized language name used everywhere downstream.
LANGUAGE_BY_EXT = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".swift": "swift",
    ".scala": "scala",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".sql": "sql",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".vue": "vue",
    ".svelte": "svelte",
    ".md": "markdown",
    ".rst": "restructuredtext",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".json": "json",
    ".xml": "xml",
}

MAX_FILE_BYTES = 1_500_000  # Skip files larger than 1.5 MB.


@dataclass
class WalkedFile:
    rel_path: str
    abs_path: Path
    size: int
    lines: int
    language: str | None


@dataclass
class WalkResult:
    files: list[WalkedFile] = field(default_factory=list)
    tree: FileNode | None = None
    dir_count: int = 0


def _load_gitignore(root: Path) -> pathspec.PathSpec:
    patterns: list[str] = []
    gi = root / ".gitignore"
    if gi.exists():
        with contextlib.suppress(OSError):
            patterns.extend(gi.read_text(errors="ignore").splitlines())
    patterns.extend(DEFAULT_IGNORE_GLOBS)
    return pathspec.PathSpec.from_lines("gitignore", patterns)


def _detect_language(path: Path) -> str | None:
    return LANGUAGE_BY_EXT.get(path.suffix.lower())


def _is_probably_text(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            chunk = f.read(2048)
    except OSError:
        return False
    return b"\x00" not in chunk


def _count_lines(path: Path) -> int:
    try:
        with path.open("rb") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def walk_project(root: Path, max_files: int | None = None) -> WalkResult:
    root = root.resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Not a directory: {root}")

    spec = _load_gitignore(root)
    result = WalkResult()
    file_index: dict[str, FileNode] = {}

    root_node = FileNode(path="", name=root.name or str(root), is_dir=True)
    file_index[""] = root_node
    result.tree = root_node

    def _ensure_dir(rel_dir: str) -> FileNode:
        if rel_dir in file_index:
            return file_index[rel_dir]
        parent_rel = "/".join(rel_dir.split("/")[:-1])
        parent = _ensure_dir(parent_rel)
        node = FileNode(path=rel_dir, name=rel_dir.split("/")[-1], is_dir=True)
        parent.children.append(node)
        file_index[rel_dir] = node
        result.dir_count += 1
        return node

    for path in sorted(root.rglob("*")):
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:
            continue

        parts = rel.split("/")
        if any(p in DEFAULT_IGNORE_DIRS for p in parts):
            continue
        if spec.match_file(rel):
            continue

        if path.is_dir():
            _ensure_dir(rel)
            continue

        if not path.is_file():
            continue

        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > MAX_FILE_BYTES:
            continue
        if not _is_probably_text(path):
            continue

        language = _detect_language(path)
        lines = _count_lines(path)

        parent_dir = "/".join(parts[:-1])
        parent = _ensure_dir(parent_dir) if parent_dir else root_node
        node = FileNode(
            path=rel, name=parts[-1], is_dir=False, size=size, lines=lines, language=language
        )
        parent.children.append(node)
        result.files.append(
            WalkedFile(
                rel_path=rel, abs_path=path, size=size, lines=lines, language=language
            )
        )
        if max_files is not None and len(result.files) >= max_files:
            break

    _sort_tree(result.tree)
    return result


def _sort_tree(node: FileNode) -> None:
    node.children.sort(key=lambda c: (not c.is_dir, c.name.lower()))
    for c in node.children:
        if c.is_dir:
            _sort_tree(c)
