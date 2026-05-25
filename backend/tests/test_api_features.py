"""API tests for brief, compare, export, and secrets endpoints."""
from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("AICARTOGRAPHER_HOME", str(tmp_path / "aic-home"))


def _mini_project(root):
    root.mkdir(parents=True, exist_ok=True)
    (root / "main.py").write_text("print('hi')\n")
    (root / "requirements.txt").write_text("requests==2.31.0\n")


def _wait_done(client: TestClient, scan_id: str, timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        s = client.get(f"/api/scans/{scan_id}").json()
        if s["state"] in {"done", "error"}:
            assert s["state"] == "done", s
            return
        time.sleep(0.1)
    raise AssertionError("scan timed out")


def test_brief_compare_export_secrets_endpoints(tmp_path):
    from aicartographer.server import create_app

    proj_a = tmp_path / "proj-a"
    proj_b = tmp_path / "proj-b"
    _mini_project(proj_a)
    _mini_project(proj_b)
    (proj_b / "extra.py").write_text("x = 1\n")

    client = TestClient(create_app())

    ra = client.post("/api/scans", json={"path": str(proj_a), "llm": "none"}).json()
    rb = client.post("/api/scans", json={"path": str(proj_b), "llm": "none"}).json()
    _wait_done(client, ra["scan_id"])
    _wait_done(client, rb["scan_id"])

    brief = client.get(f"/api/scans/{ra['scan_id']}/brief")
    assert brief.status_code == 200, brief.text
    body = brief.json()
    assert "purpose" in body
    assert "project_name" in body

    compare = client.get(
        f"/api/scans/compare?a={ra['scan_id']}&b={rb['scan_id']}"
    )
    assert compare.status_code == 200, compare.text
    diff = compare.json()
    assert "extra.py" in diff["files_added"]

    md = client.get(f"/api/scans/{ra['scan_id']}/export?format=md")
    assert md.status_code == 200
    assert "AICodeCartographer Report" in md.text

    html = client.get(f"/api/scans/{ra['scan_id']}/export?format=html")
    assert html.status_code == 200
    assert "<html" in html.text.lower()

    secrets = client.get("/api/secrets")
    assert secrets.status_code == 200
    assert secrets.json() == {"anthropic": False, "openai": False}

    set_resp = client.post(
        "/api/secrets/openai",
        json={"api_key": "sk-test-key"},
    )
    assert set_resp.status_code == 200
    assert set_resp.json()["openai"] is True

    del_resp = client.delete("/api/secrets/openai")
    assert del_resp.status_code == 200
    assert del_resp.json()["openai"] is False
