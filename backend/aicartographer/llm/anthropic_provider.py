"""Anthropic Claude provider."""
from __future__ import annotations

import logging
from typing import Any

from ..models import ModuleCard
from .base import SYSTEM_PROMPT, SummaryRequest, env, parse_response, user_prompt

log = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-3-5-haiku-latest"


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, model: str | None = None, api_key: str | None = None) -> None:
        try:
            import anthropic  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "anthropic package not installed. Run `pip install aicartographer[anthropic]`."
            ) from exc
        api_key = api_key or env("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set.")
        self.client: Any = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model or DEFAULT_MODEL

    async def summarize(self, req: SummaryRequest) -> ModuleCard:
        try:
            msg = await self.client.messages.create(
                model=self.model,
                max_tokens=600,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt(req)}],
            )
            text = ""
            for block in msg.content:
                if getattr(block, "type", None) == "text":
                    text += block.text
            return parse_response(text, req.path)
        except Exception as exc:  # noqa: BLE001
            log.warning("anthropic call failed for %s: %s", req.path, exc)
            return ModuleCard(path=req.path, summary="", status="error", error=str(exc))
