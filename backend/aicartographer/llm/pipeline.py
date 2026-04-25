"""Run the LLM summarization pipeline for a completed scan."""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from ..models import LLMKind, ModuleCard, ScanRequest
from ..parsers.treesitter import ParsedFile
from ..scanner import ScanRecord, _broadcast, _persist, _persist_status, _set_state, scan_dir
from . import cache
from .base import LLMProvider, SummaryRequest

log = logging.getLogger(__name__)

PROMPT_VERSION = "v1"
MAX_FILE_BYTES = 24_000  # ~6k tokens
MAX_FILES = 200
CONCURRENCY = 4

# Files we never bother summarizing.
SKIP_LANGS = {None, "json", "yaml", "toml", "markdown", "html", "css", "scss"}


def _select_provider(kind: LLMKind, model: str | None) -> LLMProvider | None:
    if kind == "anthropic":
        from .anthropic_provider import AnthropicProvider

        return AnthropicProvider(model=model)
    if kind == "openai":
        from .openai_provider import OpenAIProvider

        return OpenAIProvider(model=model)
    if kind == "ollama":
        from .ollama_provider import OllamaProvider

        return OllamaProvider(model=model)
    return None


def _persist_card(record: ScanRecord, card: ModuleCard) -> None:
    record.cards[card.path] = card
    d = scan_dir(record.status.scan_id) / "cards"
    d.mkdir(parents=True, exist_ok=True)
    safe = card.path.replace("/", "__")
    (d / f"{safe}.json").write_text(card.model_dump_json())
    _broadcast(record, {"type": "card", "card": card.model_dump()})


def _eligible_files(record: ScanRecord) -> list[ParsedFile]:
    parsed = list(record.parsed)
    eligible = [
        p
        for p in parsed
        if p.file.language not in SKIP_LANGS and p.file.lines >= 8
    ]
    eligible.sort(key=lambda p: p.file.lines, reverse=True)
    return eligible[:MAX_FILES]


def _neighbors_for(record: ScanRecord) -> dict[str, list[str]]:
    """Build a quick neighbor map (imports / imported-by) from on-disk deps.json."""
    p = scan_dir(record.status.scan_id) / "dependencies.json"
    if not p.exists():
        return {}
    data = json.loads(p.read_text())
    neighbors: dict[str, set[str]] = defaultdict(set)
    for e in data.get("edges", []):
        neighbors[e["source"]].add(f"-> {e['target']}")
        neighbors[e["target"]].add(f"<- {e['source']}")
    return {k: sorted(v) for k, v in neighbors.items()}


async def run_llm_pipeline(record: ScanRecord, request: ScanRequest) -> None:
    if request.llm == "none":
        return
    try:
        provider = _select_provider(request.llm, request.model)
    except Exception as exc:  # noqa: BLE001
        log.exception("provider init failed")
        record.status.error = f"LLM init failed: {exc}"
        _persist_status(record)
        _broadcast(record, {"type": "status", "status": record.status.model_dump(mode="json")})
        return
    if provider is None:
        return

    eligible = _eligible_files(record)
    record.status.progress.cards_total = len(eligible)
    record.status.progress.cards_done = 0
    _set_state(record, "summarizing", f"Summarizing {len(eligible)} files with {provider.name}/{provider.model}")

    neighbor_map = _neighbors_for(record)
    project_name = Path(record.status.root_path).name
    sem = asyncio.Semaphore(CONCURRENCY)

    async def _one(p: ParsedFile) -> None:
        try:
            try:
                code = p.file.abs_path.read_text(errors="replace")
            except OSError as exc:
                log.debug("read failed for %s: %s", p.file.rel_path, exc)
                return
            if len(code) > MAX_FILE_BYTES:
                code = code[:MAX_FILE_BYTES] + "\n# ... (truncated for summarization) ...\n"

            cached = cache.get(provider.name, provider.model, p.file.rel_path, code, PROMPT_VERSION)
            if cached is not None:
                _persist_card(record, cached)
            else:
                async with sem:
                    req = SummaryRequest(
                        path=p.file.rel_path,
                        code=code,
                        neighbors=neighbor_map.get(p.file.rel_path, []),
                        language=p.file.language,
                        project_name=project_name,
                    )
                    card = await provider.summarize(req)
                cache.put(provider.name, provider.model, p.file.rel_path, code, PROMPT_VERSION, card)
                _persist_card(record, card)
        finally:
            record.status.progress.cards_done += 1
            if record.status.progress.cards_done % 5 == 0:
                _persist_status(record)
                _broadcast(
                    record,
                    {"type": "progress", "progress": record.status.progress.model_dump()},
                )

    await asyncio.gather(*[_one(p) for p in eligible])

    # Close transient clients (e.g. Ollama httpx).
    closer = getattr(provider, "aclose", None)
    if closer is not None:
        with contextlib.suppress(Exception):
            await closer()

    record.status.finished_at = datetime.now(timezone.utc)
    _set_state(record, "done", "Summaries complete")
    _persist(record, "cards.json", {"cards": [c.model_dump() for c in record.cards.values()]})
