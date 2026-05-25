from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("AICARTOGRAPHER_HOME", str(tmp_path / "aic-home"))


def test_collect_packages_from_requirements_and_package_lock(tmp_path):
    from aicartographer.analysis import vulns as vulns_mod

    root = tmp_path / "repo"
    root.mkdir(parents=True, exist_ok=True)
    (root / "requirements.txt").write_text(
        "\n".join(
            [
                "# comment",
                "requests==2.31.0",
                "fastapi>=0.110",  # ignored (not pinned)
                "pydantic==2.7.1",
            ]
        )
    )
    (root / "package-lock.json").write_text(
        """
        {
          "name": "demo",
          "lockfileVersion": 2,
          "packages": {
            "": { "name": "demo", "version": "0.0.0" },
            "node_modules/lodash": { "name": "lodash", "version": "4.17.21" },
            "node_modules/react": { "name": "react", "version": "18.2.0" }
          }
        }
        """.strip()
    )

    pkgs = vulns_mod._collect_packages(root)
    got = {(p.ecosystem, p.name, p.version) for p in pkgs}
    assert ("PyPI", "requests", "2.31.0") in got
    assert ("PyPI", "pydantic", "2.7.1") in got
    assert ("npm", "lodash", "4.17.21") in got
    assert ("npm", "react", "18.2.0") in got
    assert not any(p[1] == "fastapi" for p in got)


def test_collect_from_pyproject_pins(tmp_path):
    from aicartographer.analysis import vulns as vulns_mod

    root = tmp_path / "repo"
    root.mkdir()
    (root / "pyproject.toml").write_text(
        """
[project]
name = "demo"
dependencies = ["requests==2.31.0", "click>=8.0"]
"""
    )
    pkgs = vulns_mod._collect_packages(root)
    assert any(p.name == "requests" and p.version == "2.31.0" for p in pkgs)


def test_osv_query_batch_is_wired(monkeypatch, tmp_path):
    from aicartographer.analysis import vulns as vulns_mod

    root = tmp_path / "repo"
    root.mkdir(parents=True, exist_ok=True)
    (root / "requirements.txt").write_text("requests==2.31.0\n")

    captured = {}

    class _Resp:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "results": [
                    {
                        "vulns": [
                            {
                                "id": "OSV-TEST-1",
                                "summary": "test vuln",
                                "references": [{"type": "ADVISORY", "url": "https://example.test"}],
                                "affected": [
                                    {
                                        "ranges": [
                                            {"events": [{"introduced": "0"}, {"fixed": "2.31.1"}]}
                                        ]
                                    }
                                ],
                            }
                        ]
                    }
                ]
            }

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def post(self, url, json):
            captured["url"] = url
            captured["json"] = json
            return _Resp()

    monkeypatch.setattr(vulns_mod.httpx, "Client", _Client)

    rep = vulns_mod.build(root)
    assert captured["url"] == vulns_mod.OSV_BATCH_URL
    assert captured["json"]["queries"][0]["package"]["ecosystem"] == "PyPI"
    assert rep.packages[0].name == "requests"
    assert rep.packages[0].vulnerabilities[0].vuln_id == "OSV-TEST-1"
    assert rep.packages[0].vulnerabilities[0].fixed == ["2.31.1"]


def test_secret_store_roundtrip_and_permissions():
    from aicartographer.secrets import configured, get_key, secrets_root, set_key

    assert configured() == {"anthropic": False, "openai": False}

    set_key("openai", "sk-test-123")
    assert get_key("openai") == "sk-test-123"
    s = configured()
    assert s["openai"] is True
    assert s["anthropic"] is False

    if os.name == "posix":
        key_path = secrets_root() / "master.key"
        enc_path = secrets_root() / "openai.enc"
        assert key_path.exists()
        assert enc_path.exists()
        assert (key_path.stat().st_mode & 0o777) == 0o600
        assert (enc_path.stat().st_mode & 0o777) == 0o600

