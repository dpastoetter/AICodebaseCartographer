"""Dependency vulnerability scanning using OSV."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import httpx

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

from ..models import (
    PackageVulnerability,
    PackageVulns,
    VulnReference,
    VulnSeverity,
    VulnsReport,
)

OSV_BATCH_URL = "https://api.osv.dev/v1/querybatch"
_SKIP_DIRS = {"node_modules", ".venv", "venv", ".git", "dist", "build"}


@dataclass(frozen=True)
class _Pkg:
    ecosystem: str
    name: str
    version: str


_REQ_PIN = re.compile(r"^\s*(?P<name>[A-Za-z0-9_.-]+)\s*==\s*(?P<version>[A-Za-z0-9+_.-]+)\s*$")
_PEP508_PIN = re.compile(r"==\s*([0-9][A-Za-z0-9+_.-]*)")
_YARN_PKG = re.compile(r'^"?(@?[^@\s"]+)@([^:\s"]+):')


def build(root: Path) -> VulnsReport:
    pkgs = _collect_packages(root)
    if not pkgs:
        return VulnsReport(packages=[])
    results = _query_osv(pkgs)
    return VulnsReport(packages=results)


def _add(out: dict[tuple[str, str, str], _Pkg], p: _Pkg) -> None:
    out[(p.ecosystem, p.name.lower(), p.version)] = p


def _collect_packages(root: Path) -> list[_Pkg]:
    out: dict[tuple[str, str, str], _Pkg] = {}

    for path in _iter_manifest_paths(root):
        name = path.name
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        if name == "requirements.txt":
            _from_requirements(text, out)
        elif name == "pyproject.toml":
            _from_pyproject(text, out)
        elif name == "poetry.lock":
            _from_poetry_lock(text, out)
        elif name == "package-lock.json":
            _from_package_lock(text, out)
        elif name == "yarn.lock":
            _from_yarn_lock(text, out)
        elif name == "pnpm-lock.yaml":
            _from_pnpm_lock(text, out)

    return list(out.values())


def _iter_manifest_paths(root: Path) -> list[Path]:
    names = {
        "requirements.txt",
        "pyproject.toml",
        "poetry.lock",
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
    }
    found: list[Path] = []
    for path in root.rglob("*"):
        if path.name not in names or not path.is_file():
            continue
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        found.append(path)
    return found


def _from_requirements(text: str, out: dict[tuple[str, str, str], _Pkg]) -> None:
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = _REQ_PIN.match(line)
        if m:
            _add(out, _Pkg("PyPI", m.group("name"), m.group("version")))


def _from_pyproject(text: str, out: dict[tuple[str, str, str], _Pkg]) -> None:
    try:
        data = tomllib.loads(text)
    except Exception:  # noqa: BLE001
        return
    project = data.get("project", {}) or {}
    for spec in project.get("dependencies", []) or []:
        _pep508_pin(str(spec), out)
    for specs in (project.get("optional-dependencies") or {}).values():
        for spec in specs:
            _pep508_pin(str(spec), out)
    poetry = (data.get("tool", {}) or {}).get("poetry", {}) or {}
    for name, ver in (poetry.get("dependencies") or {}).items():
        if name == "python":
            continue
        if isinstance(ver, str):
            m = _PEP508_PIN.search(ver)
            if m:
                _add(out, _Pkg("PyPI", str(name), m.group(1)))


def _pep508_pin(spec: str, out: dict[tuple[str, str, str], _Pkg]) -> None:
    name = re.match(r"^\s*([A-Za-z0-9_.-]+)", spec)
    if not name:
        return
    m = _PEP508_PIN.search(spec)
    if m:
        _add(out, _Pkg("PyPI", name.group(1), m.group(1)))


def _from_poetry_lock(text: str, out: dict[tuple[str, str, str], _Pkg]) -> None:
    try:
        data = tomllib.loads(text)
    except Exception:  # noqa: BLE001
        return
    for pkg in data.get("package") or []:
        if isinstance(pkg, dict) and pkg.get("name") and pkg.get("version"):
            _add(out, _Pkg("PyPI", str(pkg["name"]), str(pkg["version"])))


def _from_package_lock(text: str, out: dict[tuple[str, str, str], _Pkg]) -> None:
    try:
        data = json.loads(text)
    except Exception:  # noqa: BLE001
        return
    packages = data.get("packages") or {}
    for path_key, info in packages.items():
        if not isinstance(info, dict) or path_key == "":
            continue
        name = info.get("name")
        version = info.get("version")
        if name and version:
            _add(out, _Pkg("npm", str(name), str(version)))
    deps = data.get("dependencies") or {}
    for name, info in deps.items():
        if isinstance(info, dict) and info.get("version"):
            _add(out, _Pkg("npm", str(name), str(info["version"])))


def _from_yarn_lock(text: str, out: dict[tuple[str, str, str], _Pkg]) -> None:
    for line in text.splitlines():
        m = _YARN_PKG.match(line.strip())
        if m:
            _add(out, _Pkg("npm", m.group(1), m.group(2)))


def _from_pnpm_lock(text: str, out: dict[tuple[str, str, str], _Pkg]) -> None:
    current_name: str | None = None
    for line in text.splitlines():
        if line.startswith("  /") or line.startswith("/"):
            pkg = line.strip().split(":")[0].strip("/")
            if pkg:
                base = pkg.split("@")[-2] if "@" in pkg else pkg
                current_name = base.replace("registry.npmjs.org/", "")
        if "version:" in line and current_name:
            ver = line.split("version:", 1)[1].strip().strip("'\"")
            if ver:
                _add(out, _Pkg("npm", current_name, ver))
                current_name = None


def _query_osv(pkgs: list[_Pkg]) -> list[PackageVulns]:
    queries = [
        {"package": {"ecosystem": p.ecosystem, "name": p.name}, "version": p.version}
        for p in pkgs
    ]
    with httpx.Client(timeout=httpx.Timeout(60.0)) as client:
        r = client.post(OSV_BATCH_URL, json={"queries": queries})
        r.raise_for_status()
        data = r.json()
    resp = data.get("results") or []

    out: list[PackageVulns] = []
    for p, entry in zip(pkgs, resp, strict=False):
        vulns = entry.get("vulns") if isinstance(entry, dict) else None
        vulns_list = []
        if isinstance(vulns, list):
            for v in vulns:
                vv = _to_vuln(v)
                if vv is not None:
                    vulns_list.append(vv)
        out.append(
            PackageVulns(
                ecosystem=p.ecosystem,
                name=p.name,
                version=p.version,
                vulnerabilities=vulns_list,
            )
        )
    return out


def _to_vuln(v: dict) -> PackageVulnerability | None:
    if not isinstance(v, dict):
        return None
    vid = str(v.get("id") or "")
    if not vid:
        return None

    severity = _severity(v)
    refs = []
    for r in v.get("references") or []:
        if isinstance(r, dict) and r.get("url"):
            refs.append(VulnReference(type=r.get("type"), url=str(r["url"])))

    return PackageVulnerability(
        vuln_id=vid,
        summary=v.get("summary"),
        details=v.get("details"),
        severity=severity,
        references=refs,
        fixed=_fixed_versions(v),
    )


def _severity(v: dict) -> VulnSeverity:
    sev = v.get("severity") or []
    if isinstance(sev, list):
        for s in sev:
            if isinstance(s, dict):
                t = str(s.get("type") or "").lower()
                score = s.get("score")
                if t.startswith("cvss") and isinstance(score, str):
                    m = re.search(r"(?i)score[:=]\s*(\d+(?:\.\d+)?)", score)
                    if m:
                        return _cvss_to_bucket(float(m.group(1)))
    return "unknown"


def _cvss_to_bucket(score: float) -> VulnSeverity:
    if score >= 9.0:
        return "critical"
    if score >= 7.0:
        return "high"
    if score >= 4.0:
        return "medium"
    if score > 0:
        return "low"
    return "unknown"


def _fixed_versions(v: dict) -> list[str]:
    fixed: set[str] = set()
    for affected in v.get("affected") or []:
        if not isinstance(affected, dict):
            continue
        for rng in affected.get("ranges") or []:
            if not isinstance(rng, dict):
                continue
            for ev in rng.get("events") or []:
                if isinstance(ev, dict) and ev.get("fixed"):
                    fixed.add(str(ev["fixed"]))
    return sorted(fixed)
