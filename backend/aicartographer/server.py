"""FastAPI app exposing scan management and analysis artifacts."""
from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from importlib.resources import files as pkg_files
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

from .models import ScanFromRepoRequest, ScanRequest, ScanStatus
from .scanner import load_artifact, registry, run_scan_sync

log = logging.getLogger(__name__)


def _frontend_dist() -> Path | None:
    """Find the built frontend assets, whether running from source or wheel."""
    candidates = [
        Path(__file__).resolve().parent.parent.parent / "frontend" / "dist",
        Path(__file__).resolve().parent / "_frontend",
    ]
    for c in candidates:
        if c.exists() and (c / "index.html").exists():
            return c
    try:
        pkg_dir = Path(str(pkg_files("aicartographer").joinpath("_frontend")))
        if (pkg_dir / "index.html").exists():
            return pkg_dir
    except (ModuleNotFoundError, FileNotFoundError):
        pass
    return None


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        registry.hydrate_from_disk()
        yield

    app = FastAPI(title="AICodeCartographer", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    async def health() -> dict:
        return {"status": "ok", "version": "0.1.0"}

    @app.get("/api/scans")
    async def list_scans() -> list[ScanStatus]:
        return registry.all()

    @app.post("/api/scans")
    async def create_scan(req: ScanRequest, background: BackgroundTasks) -> ScanStatus:
        if "github.com" in req.path or req.path.startswith("git@github.com:"):
            raise HTTPException(
                status_code=400,
                detail="Looks like a GitHub repo. Use /api/scans/from-repo (or paste it into the GitHub repo input).",
            )
        target = Path(req.path).expanduser().resolve()
        if not target.exists() or not target.is_dir():
            raise HTTPException(status_code=400, detail=f"Not a directory: {target}")

        try:
            record = registry.create(req)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        async def _run() -> None:
            await asyncio.to_thread(run_scan_sync, record, req)
            if req.llm != "none":
                from .llm.pipeline import run_llm_pipeline

                try:
                    await run_llm_pipeline(record, req)
                except Exception as exc:  # noqa: BLE001
                    log.exception("LLM pipeline failed: %s", exc)
                    record.status.error = (record.status.error or "") + f" llm:{exc}"

        background.add_task(_run)
        return record.status

    @app.post("/api/scans/from-repo")
    async def create_scan_from_repo(
        req: ScanFromRepoRequest, background: BackgroundTasks
    ) -> ScanStatus:
        from .github import RepoCloneError, RepoParseError, ensure_cloned, parse_repo

        try:
            ref = parse_repo(req.repo)
            target = ensure_cloned(ref)
        except RepoParseError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RepoCloneError as exc:
            raise HTTPException(status_code=502, detail=f"Clone failed: {exc}") from exc

        scan_req = ScanRequest(
            path=str(target),
            llm=req.llm,
            model=req.model,
            max_files=req.max_files,
            api_key=req.api_key,
        )
        record = registry.create(scan_req)

        async def _run() -> None:
            await asyncio.to_thread(run_scan_sync, record, scan_req)
            if scan_req.llm != "none":
                from .llm.pipeline import run_llm_pipeline

                try:
                    await run_llm_pipeline(record, scan_req)
                except Exception as exc:  # noqa: BLE001
                    log.exception("LLM pipeline failed: %s", exc)
                    record.status.error = (record.status.error or "") + f" llm:{exc}"

        background.add_task(_run)
        return record.status

    @app.get("/api/scans/{scan_id}")
    async def get_scan(scan_id: str) -> ScanStatus:
        record = registry.get(scan_id)
        if not record:
            raise HTTPException(status_code=404, detail="Scan not found")
        return record.status

    def _artifact(scan_id: str, name: str) -> JSONResponse:
        record = registry.get(scan_id)
        if not record:
            raise HTTPException(status_code=404, detail="Scan not found")
        data = load_artifact(scan_id, name)
        if data is None:
            raise HTTPException(status_code=404, detail=f"Artifact {name} not ready")
        return JSONResponse(data)

    @app.get("/api/scans/{scan_id}/tree")
    async def get_tree(scan_id: str) -> JSONResponse:
        return _artifact(scan_id, "tree.json")

    @app.get("/api/scans/{scan_id}/dependencies")
    async def get_deps(scan_id: str) -> JSONResponse:
        return _artifact(scan_id, "dependencies.json")

    @app.get("/api/scans/{scan_id}/symbols")
    async def get_symbols(scan_id: str) -> JSONResponse:
        return _artifact(scan_id, "symbols.json")

    @app.get("/api/scans/{scan_id}/tech")
    async def get_tech(scan_id: str) -> JSONResponse:
        return _artifact(scan_id, "tech.json")

    @app.get("/api/scans/{scan_id}/hotspots")
    async def get_hotspots(scan_id: str) -> JSONResponse:
        return _artifact(scan_id, "hotspots.json")

    @app.get("/api/scans/{scan_id}/risks")
    async def get_risks(scan_id: str) -> JSONResponse:
        return _artifact(scan_id, "risks.json")

    @app.get("/api/scans/{scan_id}/cards")
    async def get_cards(scan_id: str) -> JSONResponse:
        record = registry.get(scan_id)
        if not record:
            raise HTTPException(status_code=404, detail="Scan not found")
        return JSONResponse(
            {"cards": [c.model_dump() for c in record.cards.values()]}
        )

    @app.get("/api/scans/{scan_id}/events")
    async def stream_events(scan_id: str) -> EventSourceResponse:
        record = registry.get(scan_id)
        if not record:
            raise HTTPException(status_code=404, detail="Scan not found")

        queue: asyncio.Queue = asyncio.Queue(maxsize=512)
        record.listeners.append(queue)
        queue.put_nowait({"type": "status", "status": record.status.model_dump(mode="json")})
        for card in record.cards.values():
            queue.put_nowait({"type": "card", "card": card.model_dump()})

        async def _gen():
            try:
                while True:
                    event = await queue.get()
                    yield {"event": event["type"], "data": json.dumps(event)}
                    if event["type"] == "status":
                        state = event["status"].get("state")
                        prog = record.status.progress
                        cards_complete = (
                            prog.cards_total == 0 or prog.cards_done >= prog.cards_total
                        )
                        if state in {"done", "error"} and cards_complete:
                            return
            except asyncio.CancelledError:
                pass
            finally:
                if queue in record.listeners:
                    record.listeners.remove(queue)

        return EventSourceResponse(_gen())

    dist = _frontend_dist()
    if dist is not None:
        assets = dist / "assets"
        if assets.exists():
            app.mount("/assets", StaticFiles(directory=str(assets)), name="assets")

        @app.get("/{full_path:path}")
        async def spa_fallback(full_path: str):  # noqa: ARG001
            if full_path.startswith("api/"):
                raise HTTPException(status_code=404)
            target = dist / full_path
            if target.exists() and target.is_file():
                return FileResponse(target)
            return FileResponse(dist / "index.html")
    else:

        @app.get("/")
        async def index_placeholder() -> dict:
            return {
                "status": "ok",
                "message": (
                    "Frontend not built. Run `cd frontend && npm install && npm run build`,"
                    " or run `npm run dev` and open http://localhost:5173."
                ),
            }

    return app


app = create_app()
