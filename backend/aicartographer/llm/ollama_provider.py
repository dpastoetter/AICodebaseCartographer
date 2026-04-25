"""Local Ollama provider via the standard /api/chat endpoint."""
from __future__ import annotations

import logging
import os

import httpx

from ..models import ModuleCard
from .base import SYSTEM_PROMPT, SummaryRequest, parse_response, user_prompt

log = logging.getLogger(__name__)

DEFAULT_MODEL = "llama3.1"
DEFAULT_HOST = "http://127.0.0.1:11434"


class OllamaProvider:
    name = "ollama"

    def __init__(self, model: str | None = None) -> None:
        self.model = model or DEFAULT_MODEL
        self.host = os.environ.get("OLLAMA_HOST", DEFAULT_HOST)
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))

    async def summarize(self, req: SummaryRequest) -> ModuleCard:
        try:
            r = await self.client.post(
                f"{self.host}/api/chat",
                json={
                    "model": self.model,
                    "stream": False,
                    "options": {"temperature": 0.2},
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt(req)},
                    ],
                },
            )
            r.raise_for_status()
            data = r.json()
            text = data.get("message", {}).get("content", "") or ""
            return parse_response(text, req.path)
        except Exception as exc:  # noqa: BLE001
            log.warning("ollama call failed for %s: %s", req.path, exc)
            return ModuleCard(path=req.path, summary="", status="error", error=str(exc))

    async def aclose(self) -> None:
        await self.client.aclose()
