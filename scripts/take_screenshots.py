"""Take screenshots of the AICodeCartographer dashboard for the README.

Runs end-to-end against the project itself:

1. Starts a fresh uvicorn server on a free port with an isolated
   AICARTOGRAPHER_HOME so we don't touch the user's real cache.
2. Scans this repo via the public API.
3. Drops a handful of demo ModuleCard JSON files so the "Module cards"
   view has content to display without spending real LLM tokens.
4. Drives the dashboard with Playwright, switching views via the
   sidebar buttons, and saves PNGs under docs/screenshots/.

Run from the repo root with the project venv:

    python scripts/take_screenshots.py
"""
from __future__ import annotations

import json
import os
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path

import httpx
import uvicorn

REPO_ROOT = Path(__file__).resolve().parent.parent
SHOTS_DIR = REPO_ROOT / "docs" / "screenshots"
VIEWPORT = {"width": 1440, "height": 900}


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _start_server(port: int, home: Path) -> threading.Thread:
    os.environ["AICARTOGRAPHER_HOME"] = str(home)
    sys.path.insert(0, str(REPO_ROOT / "backend"))

    from aicartographer.server import app  # noqa: E402

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    for _ in range(60):
        try:
            httpx.get(f"http://127.0.0.1:{port}/api/health", timeout=1).raise_for_status()
            return t
        except Exception:
            time.sleep(0.25)
    raise RuntimeError("server did not come up")


def _run_scan(base: str) -> str:
    r = httpx.post(
        f"{base}/api/scans",
        json={"path": str(REPO_ROOT), "llm": "none"},
        timeout=10,
    )
    r.raise_for_status()
    scan_id = r.json()["scan_id"]
    deadline = time.time() + 120
    last = ""
    while time.time() < deadline:
        s = httpx.get(f"{base}/api/scans/{scan_id}", timeout=5).json()
        if s["state"] != last:
            print(f"  scan: {s['state']} ({s['totals']['files']} files)")
            last = s["state"]
        if s["state"] in {"done", "error"}:
            if s["state"] == "error":
                raise RuntimeError(f"scan failed: {s.get('error')}")
            return scan_id
        time.sleep(0.4)
    raise RuntimeError("scan timed out")


DEMO_CARDS = [
    {
        "path": "backend/aicartographer/scanner.py",
        "summary": (
            "Top-level orchestrator that walks a project, parses every supported file with "
            "tree-sitter, runs the analysis pipeline, persists JSON snapshots, and broadcasts "
            "live SSE progress to any subscribed clients."
        ),
        "responsibilities": [
            "Coordinate walker, parser and analysis stages",
            "Maintain per-scan in-memory state and listener queues",
            "Persist artifacts under ~/.aicartographer/scans/<id>/",
        ],
        "key_symbols": ["ScanRecord", "ScanRegistry", "run_scan_sync"],
        "tech": ["Python", "asyncio", "Pydantic"],
        "status": "ready",
    },
    {
        "path": "backend/aicartographer/parsers/treesitter.py",
        "summary": (
            "Tree-sitter front end. Loads pre-compiled grammars for Python, JavaScript, "
            "TypeScript and TSX, runs language-specific queries to extract imports, classes, "
            "functions and best-effort call edges, and caches parsers per language."
        ),
        "responsibilities": [
            "Pick the right grammar by file extension",
            "Extract imports, symbols and references",
            "Cache parsers/queries with functools.cache",
        ],
        "key_symbols": ["parse_file", "_language_for", "_query_for"],
        "tech": ["tree-sitter", "Python"],
        "status": "ready",
    },
    {
        "path": "backend/aicartographer/analysis/deps.py",
        "summary": (
            "Builds the file-level import graph. Resolves Python dotted modules and JS/TS "
            "relative paths to actual files inside the repository, marks unresolved targets "
            "as external, and computes fan-in/fan-out per node."
        ),
        "responsibilities": [
            "Index the project for module lookup",
            "Resolve imports per language",
            "Emit DepNode/DepEdge records",
        ],
        "key_symbols": ["build", "_resolve_import", "fan_in_out"],
        "tech": ["Python"],
        "status": "ready",
    },
    {
        "path": "frontend/src/components/CytoscapeView.tsx",
        "summary": (
            "Reusable Cytoscape wrapper used by both the dependency and symbol graphs. "
            "Wires up the fcose layout, color-codes nodes by group, scales node size to a "
            "metric, and highlights the neighborhood of the selected node."
        ),
        "responsibilities": [
            "Mount Cytoscape with fcose layout",
            "Bind selection state to the global store",
            "Highlight neighborhood on click",
        ],
        "key_symbols": ["CytoscapeView", "selectionStyle"],
        "tech": ["React", "Cytoscape", "TypeScript"],
        "status": "ready",
    },
    {
        "path": "frontend/src/views/Mindmap.tsx",
        "summary": (
            "Renders the project's folder/file tree as an interactive markmap. Nodes are "
            "decorated with language icons and line counts and click events are forwarded "
            "to the global store for the detail panel."
        ),
        "responsibilities": [
            "Convert the tree response to markdown",
            "Mount markmap-view onto an SVG",
            "Handle click-to-select",
        ],
        "key_symbols": ["Mindmap", "pathFromLabel"],
        "tech": ["React", "markmap", "TypeScript"],
        "status": "ready",
    },
    {
        "path": "backend/aicartographer/llm/pipeline.py",
        "summary": (
            "Async summarization pipeline. Selects eligible source files, dispatches them "
            "to the chosen LLM provider with a concurrency limit, caches every result on "
            "disk by content hash, and streams cards to the UI as soon as they're ready."
        ),
        "responsibilities": [
            "Filter eligible files by language and size",
            "Coordinate a Semaphore-bounded gather",
            "Cache and broadcast each card",
        ],
        "key_symbols": ["run_llm_pipeline", "_persist_card"],
        "tech": ["asyncio", "Anthropic", "OpenAI", "Ollama"],
        "status": "ready",
    },
]


def _seed_module_cards(home: Path, scan_id: str) -> None:
    """Drop demo cards into the in-memory registry and on disk so the Module
    Cards view has content to show without spending real LLM tokens."""
    from aicartographer.models import LLMInfo, ModuleCard
    from aicartographer.scanner import registry

    record = registry.get(scan_id)
    if record is None:
        raise RuntimeError("scan record vanished")
    record.status.llm = LLMInfo(kind="anthropic", model="claude-3-5-haiku-latest (demo)")
    record.status.progress.cards_total = len(DEMO_CARDS)
    record.status.progress.cards_done = len(DEMO_CARDS)

    cards_dir = home / "scans" / scan_id / "cards"
    cards_dir.mkdir(parents=True, exist_ok=True)
    for c in DEMO_CARDS:
        card = ModuleCard.model_validate(c)
        record.cards[card.path] = card
        safe = card.path.replace("/", "__")
        (cards_dir / f"{safe}.json").write_text(card.model_dump_json())

    (home / "scans" / scan_id / "status.json").write_text(
        record.status.model_dump_json(indent=2)
    )
    (home / "scans" / scan_id / "cards.json").write_text(
        json.dumps({"cards": [c.model_dump() for c in record.cards.values()]}, indent=2)
    )


def _shoot(page, name: str) -> None:
    out = SHOTS_DIR / f"{name}.png"
    page.screenshot(path=str(out), full_page=False)
    print(f"  saved {out.relative_to(REPO_ROOT)}")


def main() -> None:
    SHOTS_DIR.mkdir(parents=True, exist_ok=True)
    home = Path(tempfile.mkdtemp(prefix="aic-shots-"))
    port = _free_port()
    base = f"http://127.0.0.1:{port}"
    print(f"== AICARTOGRAPHER_HOME={home}")
    print(f"== server: {base}")

    _start_server(port, home)
    print("== server up")

    scan_id = _run_scan(base)
    print(f"== scan complete: {scan_id}")

    _seed_module_cards(home, scan_id)
    print("== seeded demo module cards")

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport=VIEWPORT, device_scale_factor=2)
        page = ctx.new_page()

        page.goto(base, wait_until="networkidle")
        # StartPanel headline changed during UI polish; wait for a stable marker.
        page.wait_for_selector("text=New analysis")
        time.sleep(0.5)
        _shoot(page, "01-welcome")

        page.goto(f"{base}/?scan={scan_id}", wait_until="networkidle")
        page.wait_for_selector("nav button:has-text('Structure')")
        time.sleep(2.0)
        _shoot(page, "02-mindmap")

        for label, name in [
            ("Dependencies", "03-dependencies"),
            ("Symbols", "04-symbols"),
            ("Summaries", "05-module-cards"),
            ("Technology", "06-tech-radar"),
            ("Hotspots", "07-hotspots"),
        ]:
            page.click(f"nav button:has-text('{label}')")
            time.sleep(2.0 if "graph" in label.lower() or label in {"Dependencies", "Symbols"} else 1.0)
            _shoot(page, name)

        browser.close()

    print(f"== done -> {SHOTS_DIR}")


if __name__ == "__main__":
    main()
