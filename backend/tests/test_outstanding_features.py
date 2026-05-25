"""Tests for Ask, architecture map, search, MCP tools, and review helpers."""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from aicartographer.analysis.layers import build_for_scan
from aicartographer.ask import build_context, neighbors_for_path
from aicartographer.mcp_server import _call_tool
from aicartographer.models import DepEdge, DependencyGraph, DepNode
from aicartographer.search_index import search_codebase


def test_search_codebase_empty():
    assert search_codebase("nonexistent-scan-xyz", "foo") == []


def test_neighbors_empty():
    assert neighbors_for_path("nonexistent", "a.py") == {"imports": [], "imported_by": []}


def test_build_context_missing():
    ctx = build_context("missing-id", __import__("pathlib").Path("/tmp"))
    assert "Repo root" in ctx


def test_layers_from_graph():
    deps = DependencyGraph(
        nodes=[
            DepNode(id="src/a.py", label="a.py", lines=10, group="src"),
            DepNode(id="lib/b.py", label="b.py", lines=5, group="lib"),
        ],
        edges=[DepEdge(source="src/a.py", target="lib/b.py")],
    )
    from aicartographer.analysis.layers import build_from_graph

    amap = build_from_graph(deps)
    assert len(amap.layers) == 2
    assert any(e.source == "src" and e.target == "lib" for e in amap.edges)


def test_mcp_list_scans():

    result = _call_tool("list_scans", {})
    assert "content" in result
    data = json.loads(result["content"][0]["text"])
    assert isinstance(data, list)


def test_mcp_search_requires_scan():
    with pytest.raises(ValueError, match="not ready|not found|risks"):
        _call_tool("get_risks", {"scan_id": "does-not-exist-abc"})


@patch("aicartographer.review._scan_path", side_effect=lambda p, req: f"scan-{p.name}")
@patch("aicartographer.review._checkout_worktree")
@patch("aicartographer.review._resolve_repo_path")
def test_run_review(mock_resolve, mock_wt, mock_scan):
    from pathlib import Path

    from aicartographer.models import ScanReviewRequest
    from aicartographer.review import run_review

    repo = Path("/fake/repo")
    mock_resolve.return_value = repo
    base = Path("/tmp/base")
    head = Path("/tmp/head")
    mock_wt.side_effect = [base, head]

    with patch("aicartographer.review.compare_scans") as mock_cmp:
        from aicartographer.models import ScanCompareResult

        mock_cmp.return_value = ScanCompareResult(
            scan_a="scan-base",
            scan_b="scan-head",
            files_added=["new.py"],
            risks_added=["r1"],
        )
        with patch("aicartographer.review._cleanup_worktree"):
            result = run_review(ScanReviewRequest(repo=str(repo), base="main", head="feature"))
    assert result.scan_base == "scan-base"
    assert result.scan_head == "scan-head"
    assert "files added" in result.summary


def test_build_for_scan_none():
    assert build_for_scan("no-such-scan-id") is None
