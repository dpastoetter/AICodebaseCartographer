"""MCP stdio server exposing scan intelligence to Cursor and other agents."""
from __future__ import annotations

import json
import logging
import sys
from typing import Any

from .analysis.layers import build_for_scan
from .ask import neighbors_for_path
from .models import ArchitectureBrief
from .scanner import load_artifact, registry
from .search_index import search_codebase

log = logging.getLogger(__name__)

TOOLS = [
    {
        "name": "get_brief",
        "description": "Architecture brief for a completed scan (scan_id).",
        "inputSchema": {
            "type": "object",
            "properties": {"scan_id": {"type": "string"}},
            "required": ["scan_id"],
        },
    },
    {
        "name": "search_codebase",
        "description": "Search files, symbols, risks, vulns, and module cards in a scan.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "scan_id": {"type": "string"},
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 25},
            },
            "required": ["scan_id", "query"],
        },
    },
    {
        "name": "get_risks",
        "description": "Heuristic security findings for a scan.",
        "inputSchema": {
            "type": "object",
            "properties": {"scan_id": {"type": "string"}},
            "required": ["scan_id"],
        },
    },
    {
        "name": "get_vulns",
        "description": "OSV dependency vulnerabilities for a scan.",
        "inputSchema": {
            "type": "object",
            "properties": {"scan_id": {"type": "string"}},
            "required": ["scan_id"],
        },
    },
    {
        "name": "get_file_neighbors",
        "description": "Import graph neighbors for a file path within a scan.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "scan_id": {"type": "string"},
                "path": {"type": "string"},
            },
            "required": ["scan_id", "path"],
        },
    },
    {
        "name": "get_architecture_map",
        "description": "Layered architecture map (folder clusters + cross-layer imports).",
        "inputSchema": {
            "type": "object",
            "properties": {"scan_id": {"type": "string"}},
            "required": ["scan_id"],
        },
    },
    {
        "name": "list_scans",
        "description": "List known scan ids and root paths.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def _tool_result(data: Any) -> dict:
    text = json.dumps(data, indent=2, default=str)
    return {"content": [{"type": "text", "text": text}]}


def _call_tool(name: str, arguments: dict) -> dict:
    if name == "list_scans":
        return _tool_result(
            [
                {"scan_id": s.scan_id, "root_path": s.root_path, "state": s.state}
                for s in registry.all()
            ]
        )
    scan_id = arguments.get("scan_id", "")
    if name == "get_brief":
        data = load_artifact(scan_id, "brief.json")
        if data is None:
            record = registry.get(scan_id)
            if not record:
                raise ValueError(f"Scan not found: {scan_id}")
            walk = record.walk
            if walk is None:
                raise ValueError("Scan artifacts not ready")
            brief = build_brief_from_record(scan_id, record)
            return _tool_result(brief.model_dump())
        return _tool_result(data)
    if name == "search_codebase":
        return _tool_result(
            search_codebase(scan_id, arguments["query"], limit=int(arguments.get("limit", 25)))
        )
    if name == "get_risks":
        data = load_artifact(scan_id, "risks.json")
        if data is None:
            raise ValueError("risks.json not ready")
        return _tool_result(data)
    if name == "get_vulns":
        data = load_artifact(scan_id, "vulns.json")
        if data is None:
            raise ValueError("vulns.json not ready")
        return _tool_result(data)
    if name == "get_file_neighbors":
        return _tool_result(neighbors_for_path(scan_id, arguments["path"]))
    if name == "get_architecture_map":
        amap = build_for_scan(scan_id)
        if amap is None:
            raise ValueError("dependencies.json not ready")
        return _tool_result(amap.model_dump())
    raise ValueError(f"Unknown tool: {name}")


def build_brief_from_record(scan_id: str, record) -> ArchitectureBrief:
    from pathlib import Path

    from .analysis.brief import build as build_brief_fn
    from .models import DependencyGraph, Hotspots, RisksReport, TechRadar, VulnsReport

    root = Path(record.status.root_path)
    walk = record.walk
    tech = TechRadar.model_validate(load_artifact(scan_id, "tech.json") or {})
    deps = DependencyGraph.model_validate(load_artifact(scan_id, "dependencies.json") or {})
    spots = Hotspots.model_validate(load_artifact(scan_id, "hotspots.json") or {})
    risks = RisksReport.model_validate(load_artifact(scan_id, "risks.json") or {})
    vulns = VulnsReport.model_validate(load_artifact(scan_id, "vulns.json") or {})
    return build_brief_fn(root, walk, tech, deps, spots, risks, vulns)


def _handle_message(msg: dict) -> dict | None:
    method = msg.get("method")
    msg_id = msg.get("id")
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "aicartographer", "version": "0.1.0"},
            },
        }
    if method == "notifications/initialized":
        return None
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = msg.get("params") or {}
        try:
            result = _call_tool(params.get("name", ""), params.get("arguments") or {})
            return {"jsonrpc": "2.0", "id": msg_id, "result": result}
        except Exception as exc:  # noqa: BLE001
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"content": [{"type": "text", "text": str(exc)}], "isError": True},
            }
    if method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}
    if msg_id is not None:
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }
    return None


def run_stdio() -> None:
    registry.hydrate_from_disk()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        resp = _handle_message(msg)
        if resp:
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
