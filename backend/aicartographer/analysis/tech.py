"""Tech radar: detect languages, frameworks, libraries from manifests."""
from __future__ import annotations

import json
import logging
import re
from collections import Counter
from pathlib import Path

try:
    import tomllib  # type: ignore[attr-defined]
except ModuleNotFoundError:  # pragma: no cover - py<3.11 fallback
    import tomli as tomllib  # type: ignore[no-redef]

from ..models import LanguageStat, TechItem, TechRadar
from ..parsers.treesitter import ParsedFile
from ..walker import WalkResult

log = logging.getLogger(__name__)


KNOWN_FRAMEWORKS: dict[str, tuple[str, str]] = {
    # JS / TS
    "react": ("UI framework", "framework"),
    "react-dom": ("UI framework", "framework"),
    "vue": ("UI framework", "framework"),
    "@angular/core": ("UI framework", "framework"),
    "svelte": ("UI framework", "framework"),
    "next": ("Web framework", "framework"),
    "nuxt": ("Web framework", "framework"),
    "express": ("Web framework", "framework"),
    "fastify": ("Web framework", "framework"),
    "nestjs": ("Web framework", "framework"),
    "@nestjs/core": ("Web framework", "framework"),
    "remix": ("Web framework", "framework"),
    "astro": ("Web framework", "framework"),
    "vite": ("Build tool", "tool"),
    "webpack": ("Build tool", "tool"),
    "rollup": ("Build tool", "tool"),
    "tailwindcss": ("Styling", "library"),
    "typescript": ("Language", "language"),
    "jest": ("Testing", "tool"),
    "vitest": ("Testing", "tool"),
    "playwright": ("Testing", "tool"),
    "cypress": ("Testing", "tool"),
    "zustand": ("State management", "library"),
    "redux": ("State management", "library"),
    "@reduxjs/toolkit": ("State management", "library"),
    "react-query": ("Data fetching", "library"),
    "@tanstack/react-query": ("Data fetching", "library"),
    "axios": ("HTTP client", "library"),
    "cytoscape": ("Visualization", "library"),
    "d3": ("Visualization", "library"),
    "recharts": ("Visualization", "library"),
    # Python
    "fastapi": ("Web framework", "framework"),
    "starlette": ("Web framework", "framework"),
    "django": ("Web framework", "framework"),
    "flask": ("Web framework", "framework"),
    "pyramid": ("Web framework", "framework"),
    "tornado": ("Web framework", "framework"),
    "uvicorn": ("ASGI server", "runtime"),
    "gunicorn": ("WSGI server", "runtime"),
    "sqlalchemy": ("ORM", "library"),
    "alembic": ("Migrations", "library"),
    "pydantic": ("Validation", "library"),
    "pandas": ("Data", "library"),
    "numpy": ("Data", "library"),
    "torch": ("ML", "library"),
    "tensorflow": ("ML", "library"),
    "scikit-learn": ("ML", "library"),
    "pytest": ("Testing", "tool"),
    "ruff": ("Linting", "tool"),
    "mypy": ("Type-checking", "tool"),
    "anthropic": ("LLM SDK", "library"),
    "openai": ("LLM SDK", "library"),
    "tree-sitter": ("Parsing", "library"),
    # Rust / Go
    "axum": ("Web framework", "framework"),
    "actix-web": ("Web framework", "framework"),
    "rocket": ("Web framework", "framework"),
    "tokio": ("Async runtime", "runtime"),
    "gin-gonic": ("Web framework", "framework"),
    "echo": ("Web framework", "framework"),
}


def build(root: Path, walk: WalkResult, parsed: list[ParsedFile]) -> TechRadar:  # noqa: ARG001
    languages = _language_stats(walk)
    items: list[TechItem] = []
    seen: set[tuple[str, str]] = set()

    def add(item: TechItem) -> None:
        key = (item.name.lower(), item.source)
        if key in seen:
            return
        seen.add(key)
        items.append(item)

    for path, content in _read_manifests(root):
        rel = path.relative_to(root).as_posix()
        try:
            for item in _parse_manifest(rel, content):
                add(item)
        except Exception as exc:  # noqa: BLE001
            log.debug("manifest parse failed for %s: %s", rel, exc)

    return TechRadar(languages=languages, items=items)


def _language_stats(walk: WalkResult) -> list[LanguageStat]:
    files: Counter[str] = Counter()
    lines: Counter[str] = Counter()
    for f in walk.files:
        if not f.language:
            continue
        files[f.language] += 1
        lines[f.language] += f.lines
    stats = [
        LanguageStat(name=name, files=files[name], lines=lines[name])
        for name in files
    ]
    stats.sort(key=lambda s: (-s.lines, -s.files, s.name))
    return stats


_MANIFESTS = {
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "Pipfile",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "Gemfile",
    "composer.json",
}


def _read_manifests(root: Path) -> list[tuple[Path, str]]:
    out: list[tuple[Path, str]] = []
    for path in root.rglob("*"):
        if path.name in _MANIFESTS and path.is_file():
            try:
                if any(part in {"node_modules", ".venv", "venv"} for part in path.parts):
                    continue
                out.append((path, path.read_text(errors="ignore")))
            except OSError:
                continue
    return out


def _parse_manifest(rel: str, content: str) -> list[TechItem]:
    name = rel.rsplit("/", 1)[-1]
    if name == "package.json":
        return _from_package_json(rel, content)
    if name == "pyproject.toml":
        return _from_pyproject(rel, content)
    if name == "requirements.txt":
        return _from_requirements(rel, content)
    if name == "Pipfile":
        return _from_pipfile(rel, content)
    if name == "Cargo.toml":
        return _from_cargo(rel, content)
    if name == "go.mod":
        return _from_gomod(rel, content)
    if name == "pom.xml":
        return _from_pom(rel, content)
    if name == "Gemfile":
        return _from_gemfile(rel, content)
    if name == "composer.json":
        return _from_composer(rel, content)
    return []


def _make_item(name: str, version: str | None, source: str) -> TechItem:
    info = KNOWN_FRAMEWORKS.get(name.lower())
    if info:
        category, kind = info
        return TechItem(
            name=name, kind=kind, version=version, source=source, category=category
        )
    return TechItem(name=name, kind="library", version=version, source=source)


def _from_package_json(source: str, content: str) -> list[TechItem]:
    data = json.loads(content)
    items: list[TechItem] = []
    for section in ("dependencies", "devDependencies", "peerDependencies"):
        deps = data.get(section, {}) or {}
        for name, version in deps.items():
            items.append(_make_item(name, str(version), source))
    return items


def _from_pyproject(source: str, content: str) -> list[TechItem]:
    data = tomllib.loads(content)
    items: list[TechItem] = []
    project = data.get("project", {}) or {}
    for spec in project.get("dependencies", []) or []:
        n, v = _split_pep508(spec)
        items.append(_make_item(n, v, source))
    optional = project.get("optional-dependencies", {}) or {}
    for specs in optional.values():
        for spec in specs:
            n, v = _split_pep508(spec)
            items.append(_make_item(n, v, source))
    poetry_deps = (
        data.get("tool", {}).get("poetry", {}).get("dependencies", {}) or {}
    )
    for name, ver in poetry_deps.items():
        if name == "python":
            continue
        version = ver if isinstance(ver, str) else None
        items.append(_make_item(name, version, source))
    return items


_PEP508_RE = re.compile(
    r"^\s*(?P<name>[A-Za-z0-9_.\-]+)"
    r"(?:\[[^\]]*\])?"
    r"\s*(?P<rest>.*)$"
)


def _split_pep508(spec: str) -> tuple[str, str | None]:
    m = _PEP508_RE.match(spec)
    if not m:
        return spec.strip(), None
    rest = m.group("rest").strip()
    rest = rest.split(";", 1)[0].strip()
    return m.group("name"), (rest or None)


def _from_requirements(source: str, content: str) -> list[TechItem]:
    items: list[TechItem] = []
    for line in content.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        n, v = _split_pep508(line)
        items.append(_make_item(n, v, source))
    return items


def _from_pipfile(source: str, content: str) -> list[TechItem]:
    data = tomllib.loads(content)
    items: list[TechItem] = []
    for section in ("packages", "dev-packages"):
        for name, ver in (data.get(section, {}) or {}).items():
            version = ver if isinstance(ver, str) else None
            items.append(_make_item(name, version, source))
    return items


def _from_cargo(source: str, content: str) -> list[TechItem]:
    data = tomllib.loads(content)
    items: list[TechItem] = []
    for section in ("dependencies", "dev-dependencies", "build-dependencies"):
        for name, ver in (data.get(section, {}) or {}).items():
            version = ver if isinstance(ver, str) else (ver.get("version") if isinstance(ver, dict) else None)
            items.append(_make_item(name, version, source))
    return items


_GOMOD_REQUIRE_RE = re.compile(r"^\s*([\w./\-]+)\s+([\w.\-+]+)")


def _from_gomod(source: str, content: str) -> list[TechItem]:
    items: list[TechItem] = []
    inside = False
    for line in content.splitlines():
        s = line.strip()
        if s.startswith("require ("):
            inside = True
            continue
        if inside and s == ")":
            inside = False
            continue
        if inside:
            m = _GOMOD_REQUIRE_RE.match(line)
            if m:
                items.append(_make_item(m.group(1), m.group(2), source))
            continue
        if s.startswith("require "):
            m = _GOMOD_REQUIRE_RE.match(line.replace("require ", "", 1))
            if m:
                items.append(_make_item(m.group(1), m.group(2), source))
    return items


_POM_DEP_RE = re.compile(
    r"<dependency>(.*?)</dependency>", re.DOTALL
)
_POM_FIELD_RE = re.compile(r"<(\w+)>([^<]+)</\1>")


def _from_pom(source: str, content: str) -> list[TechItem]:
    items: list[TechItem] = []
    for block in _POM_DEP_RE.findall(content):
        fields = dict(_POM_FIELD_RE.findall(block))
        name = ":".join(filter(None, [fields.get("groupId"), fields.get("artifactId")]))
        if name:
            items.append(_make_item(name, fields.get("version"), source))
    return items


def _from_gemfile(source: str, content: str) -> list[TechItem]:
    items: list[TechItem] = []
    pat = re.compile(r"gem\s+['\"]([^'\"]+)['\"](?:\s*,\s*['\"]([^'\"]+)['\"])?")
    for m in pat.finditer(content):
        items.append(_make_item(m.group(1), m.group(2), source))
    return items


def _from_composer(source: str, content: str) -> list[TechItem]:
    data = json.loads(content)
    items: list[TechItem] = []
    for section in ("require", "require-dev"):
        for name, ver in (data.get(section, {}) or {}).items():
            items.append(_make_item(name, str(ver) if ver else None, source))
    return items
