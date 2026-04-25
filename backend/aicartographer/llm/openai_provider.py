"""OpenAI provider."""
from __future__ import annotations

import logging
from typing import Any

from ..models import ModuleCard
from .base import SYSTEM_PROMPT, SummaryRequest, env, parse_response, user_prompt

log = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-4o-mini"


class OpenAIProvider:
    name = "openai"

    def __init__(self, model: str | None = None) -> None:
        try:
            import openai  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "openai package not installed. Run `pip install aicartographer[openai]`."
            ) from exc
        api_key = env("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set.")
        self.client: Any = openai.AsyncOpenAI(api_key=api_key)
        self.model = model or DEFAULT_MODEL

    async def summarize(self, req: SummaryRequest) -> ModuleCard:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                temperature=0.2,
                max_tokens=600,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt(req)},
                ],
            )
            text = response.choices[0].message.content or ""
            return parse_response(text, req.path)
        except Exception as exc:  # noqa: BLE001
            log.warning("openai call failed for %s: %s", req.path, exc)
            return ModuleCard(path=req.path, summary="", status="error", error=str(exc))
