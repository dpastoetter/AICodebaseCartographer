"""LLM provider abstraction."""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Protocol

from ..models import LLMKind, ModuleCard

log = logging.getLogger(__name__)


@dataclass
class SummaryRequest:
    path: str
    code: str
    neighbors: list[str]
    language: str | None
    project_name: str


class LLMProvider(Protocol):
    name: LLMKind
    model: str

    async def summarize(self, req: SummaryRequest) -> ModuleCard: ...


SYSTEM_PROMPT = """You are AICodeCartographer's analyst. For each source file you receive,
write a concise, accurate technical summary aimed at an engineer new to the codebase.

Respond ONLY with valid minified JSON in this exact shape:
{
  "summary": "<1-3 sentences describing what the file does and why it exists>",
  "responsibilities": ["<short bullet>", "<short bullet>", "..."],
  "key_symbols": ["<class/function name>", "..."],
  "tech": ["<framework or library that this file actually uses>", "..."]
}
Keep responsibilities to at most 5 bullets. Keep names accurate; do not invent symbols.
Do not wrap the JSON in code fences."""


def user_prompt(req: SummaryRequest) -> str:
    neighbor_block = ""
    if req.neighbors:
        neighbor_block = (
            "\n\nIt imports / is imported by:\n" + "\n".join(f"- {n}" for n in req.neighbors[:20])
        )
    return (
        f"Project: {req.project_name}\n"
        f"File: {req.path}\n"
        f"Language: {req.language or 'unknown'}"
        f"{neighbor_block}\n\n"
        "Source:\n```\n"
        f"{req.code}\n```"
    )


def parse_response(raw: str, path: str) -> ModuleCard:
    """Parse model JSON output, defensively."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return ModuleCard(
            path=path,
            summary=raw[:240],
            status="error",
            error="non-json response",
        )
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        return ModuleCard(
            path=path,
            summary=raw[:240],
            status="error",
            error=f"json error: {exc}",
        )
    return ModuleCard(
        path=path,
        summary=str(data.get("summary", ""))[:1000],
        responsibilities=[str(x)[:200] for x in (data.get("responsibilities") or [])][:8],
        key_symbols=[str(x)[:100] for x in (data.get("key_symbols") or [])][:20],
        tech=[str(x)[:80] for x in (data.get("tech") or [])][:20],
        status="ready",
    )


def env(name: str) -> str | None:
    val = os.environ.get(name)
    return val.strip() if val else None
