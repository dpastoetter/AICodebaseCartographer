from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("AICARTOGRAPHER_HOME", str(tmp_path / "aic-home"))


def test_compare_scans_file_delta(tmp_path):
    from aicartographer.compare import compare_scans
    from aicartographer.storage import scan_dir

    a, b = "aaaa1111", "bbbb2222"
    for sid, files in [(a, ["a.py"]), (b, ["a.py", "b.py"])]:
        d = scan_dir(sid)
        tree = {"root": {"path": "", "name": "root", "is_dir": True, "children": []}}
        for f in files:
            tree["root"]["children"].append(
                {"path": f, "name": f, "is_dir": False, "children": []}
            )
        (d / "tree.json").write_text(__import__("json").dumps(tree))
        (d / "dependencies.json").write_text('{"nodes":[],"edges":[]}')
        (d / "risks.json").write_text('{"findings":[]}')
        (d / "vulns.json").write_text('{"packages":[]}')
        (d / "hotspots.json").write_text(
            '{"largest":[],"most_imported":[],"most_complex":[],"churn":[]}'
        )

    result = compare_scans(a, b)
    assert "b.py" in result.files_added
    assert result.files_removed == []
