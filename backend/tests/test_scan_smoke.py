"""End-to-end smoke tests against a tiny Python and TS project."""
from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("AICARTOGRAPHER_HOME", str(tmp_path / "aic-home"))


def _build_python_project(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pkg").mkdir()
    (root / "pkg" / "__init__.py").write_text("")
    (root / "pkg" / "models.py").write_text(
        "class User:\n    def __init__(self, name):\n        self.name = name\n"
    )
    (root / "pkg" / "service.py").write_text(
        "from .models import User\n\n"
        "def make_user(n):\n    return User(n)\n\n"
        "def greet(n):\n    u = make_user(n)\n    return f'hi {u.name}'\n"
    )
    (root / "main.py").write_text(
        "from pkg.service import greet\n\nif __name__ == '__main__':\n    print(greet('world'))\n"
    )
    (root / "requirements.txt").write_text("fastapi>=0.100\npydantic>=2\n")
    return root


def _build_ts_project(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    src = root / "src"
    src.mkdir()
    (src / "user.ts").write_text(
        "export class User {\n  constructor(public name: string) {}\n}\n"
    )
    (src / "service.ts").write_text(
        "import { User } from './user';\n"
        "export function makeUser(n: string) { return new User(n); }\n"
        "export function greet(n: string) { return `hi ${makeUser(n).name}`; }\n"
    )
    (src / "main.tsx").write_text(
        "import { greet } from './service';\nexport function App() { return greet('world'); }\n"
    )
    (root / "package.json").write_text(
        '{"name":"demo","dependencies":{"react":"^18.0.0","typescript":"^5.0.0"}}'
    )
    return root


def _scan(client: TestClient, path: Path) -> dict:
    r = client.post("/api/scans", json={"path": str(path), "llm": "none"})
    assert r.status_code == 200, r.text
    sid = r.json()["scan_id"]

    deadline = time.time() + 15
    while time.time() < deadline:
        s = client.get(f"/api/scans/{sid}").json()
        if s["state"] in {"done", "error"}:
            break
        time.sleep(0.1)
    s = client.get(f"/api/scans/{sid}").json()
    assert s["state"] == "done", s
    return {
        "status": s,
        "tree": client.get(f"/api/scans/{sid}/tree").json(),
        "deps": client.get(f"/api/scans/{sid}/dependencies").json(),
        "symbols": client.get(f"/api/scans/{sid}/symbols").json(),
        "tech": client.get(f"/api/scans/{sid}/tech").json(),
        "hotspots": client.get(f"/api/scans/{sid}/hotspots").json(),
    }


def test_python_project_smoke(tmp_path):
    from aicartographer.server import create_app

    proj = _build_python_project(tmp_path / "py-demo")
    client = TestClient(create_app())
    out = _scan(client, proj)

    assert out["status"]["totals"]["files"] >= 4
    dep_edges = {(e["source"], e["target"]) for e in out["deps"]["edges"]}
    assert ("pkg/service.py", "pkg/models.py") in dep_edges
    assert ("main.py", "pkg/service.py") in dep_edges

    sym_names = {n["name"] for n in out["symbols"]["nodes"]}
    assert {"User", "make_user", "greet"} <= sym_names

    langs = {lang["name"] for lang in out["tech"]["languages"]}
    assert "python" in langs
    items = {i["name"].lower() for i in out["tech"]["items"]}
    assert "fastapi" in items

    largest = out["hotspots"]["largest"]
    assert any(e["path"] == "pkg/service.py" for e in largest)


def test_ts_project_smoke(tmp_path):
    from aicartographer.server import create_app

    proj = _build_ts_project(tmp_path / "ts-demo")
    client = TestClient(create_app())
    out = _scan(client, proj)

    assert out["status"]["totals"]["files"] >= 3
    dep_edges = {(e["source"], e["target"]) for e in out["deps"]["edges"]}
    assert ("src/service.ts", "src/user.ts") in dep_edges
    assert ("src/main.tsx", "src/service.ts") in dep_edges

    sym_names = {n["name"] for n in out["symbols"]["nodes"]}
    assert {"User", "makeUser", "greet", "App"} <= sym_names

    items = {i["name"].lower() for i in out["tech"]["items"]}
    assert "react" in items
    assert "typescript" in items
