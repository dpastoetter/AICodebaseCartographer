"""Grounded Q&A over a completed scan's artifacts."""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from .llm.pipeline import _select_provider
from .models import AskCitation, AskRequest, AskResponse, LLMKind
from .scanner import load_artifact
from .secrets import get_key

log = logging.getLogger(__name__)

MAX_CONTEXT_CHARS = 72_000
MAX_EXCERPT = 4_000


def build_context(scan_id: str, root_path: Path) -> str:
    parts: list[str] = []

    brief = load_artifact(scan_id, "brief.json")
    if brief:
        parts.append("## Architecture brief\n" + json.dumps(brief, indent=0)[:8000])

    deps = load_artifact(scan_id, "dependencies.json")
    if deps:
        edges = deps.get("edges") or []
        sample = edges[:120]
        parts.append(
            f"## Dependencies ({len(edges)} edges, sample)\n"
            + json.dumps(sample, indent=0)
        )

    symbols = load_artifact(scan_id, "symbols.json")
    if symbols:
        nodes = symbols.get("nodes") or []
        parts.append(
            f"## Symbols ({len(nodes)} total, sample names)\n"
            + json.dumps(
                [{"name": n.get("name"), "file": n.get("file"), "kind": n.get("kind")} for n in nodes[:80]],
                indent=0,
            )
        )

    risks = load_artifact(scan_id, "risks.json")
    if risks:
        findings = risks.get("findings") or []
        parts.append(
            f"## Risks ({len(findings)} findings, top)\n"
            + json.dumps(findings[:40], indent=0)
        )

    vulns = load_artifact(scan_id, "vulns.json")
    if vulns:
        parts.append("## Vulnerabilities (OSV)\n" + json.dumps(vulns, indent=0)[:12000])

    cards = load_artifact(scan_id, "cards.json")
    if cards:
        for c in (cards.get("cards") or [])[:25]:
            if isinstance(c, dict) and c.get("summary"):
                parts.append(f"### Card {c.get('path')}\n{c.get('summary')}")

    text = "\n\n".join(parts)
    if len(text) > MAX_CONTEXT_CHARS:
        text = text[:MAX_CONTEXT_CHARS] + "\n\n... (context truncated)"
    parts.append(f"\n## Repo root\n{root_path}")
    return "\n\n".join(parts)


def _read_excerpt(root: Path, rel_path: str) -> str:
    p = root / rel_path
    if not p.is_file():
        return ""
    try:
        data = p.read_text(errors="replace")
    except OSError:
        return ""
    if len(data) > MAX_EXCERPT:
        return data[:MAX_EXCERPT] + "\n... (truncated)"
    return data


ASK_SYSTEM = """You are AICodeCartographer's codebase assistant. Answer using ONLY the scan context provided.
Cite evidence with paths like `src/foo.py:42` or risk/vuln ids from the context.
Respond with JSON only:
{"answer": "<markdown prose>", "citations": [{"kind":"file|risk|vuln|symbol", "label":"...", "path":"optional", "line": null or int}]}
Do not invent files or symbols not supported by the context."""


async def ask_scan(
    scan_id: str,
    root_path: Path,
    req: AskRequest,
    *,
    llm: LLMKind = "openai",
    model: str | None = None,
    api_key: str | None = None,
) -> AskResponse:
    context = build_context(scan_id, root_path)
    excerpt_block = ""
    for m in re.finditer(r"`([^`]+\.(?:py|ts|tsx|js|go|rs))(?::(\d+))?`", req.question):
        rel = m.group(1)
        excerpt = _read_excerpt(root_path, rel)
        if excerpt:
            excerpt_block += f"\n\n### File excerpt: {rel}\n```\n{excerpt}\n```"

    user = f"Context:\n{context}{excerpt_block}\n\nQuestion: {req.question}"

    kind = llm
    if api_key is None and kind in {"openai", "anthropic"}:
        api_key = get_key(kind)

    try:
        provider = _select_provider(kind, model, api_key)
    except Exception as exc:  # noqa: BLE001
        return AskResponse(answer=f"LLM unavailable: {exc}", citations=[])

    if provider is None:
        return AskResponse(
            answer="Configure an LLM provider (OpenAI/Anthropic via Keys or env) to use Ask.",
            citations=[],
        )

    text = await _chat(provider, user)
    return _parse_ask_response(text, scan_id, root_path)


async def _chat(provider, user: str) -> str:
    if provider.name == "openai":
        response = await provider.client.chat.completions.create(
            model=provider.model,
            temperature=0.2,
            max_tokens=1200,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": ASK_SYSTEM},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content or ""
    if provider.name == "anthropic":
        response = await provider.client.messages.create(
            model=provider.model,
            max_tokens=1200,
            system=ASK_SYSTEM,
            messages=[{"role": "user", "content": user}],
        )
        blocks = response.content
        return "".join(getattr(b, "text", "") for b in blocks)
    return json.dumps({"answer": "Ollama ask not wired yet.", "citations": []})


def _parse_ask_response(raw: str, scan_id: str, root: Path) -> AskResponse:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        try:
            data = json.loads(text[start : end + 1])
            citations = [
                AskCitation(
                    kind=c.get("kind", "note"),
                    label=str(c.get("label", "")),
                    path=c.get("path"),
                    line=c.get("line"),
                )
                for c in data.get("citations") or []
                if isinstance(c, dict)
            ]
            return AskResponse(
                answer=str(data.get("answer", raw)),
                citations=citations,
            )
        except json.JSONDecodeError:
            pass

    citations = _extract_path_citations(raw, root)
    return AskResponse(answer=raw, citations=citations)


def _extract_path_citations(text: str, root: Path) -> list[AskCitation]:
    out: list[AskCitation] = []
    for m in re.finditer(r"`?([A-Za-z0-9_./-]+\.(?:py|ts|tsx|js))(?::(\d+))?`?", text):
        path = m.group(1)
        line = int(m.group(2)) if m.group(2) else None
        if (root / path).exists():
            out.append(AskCitation(kind="file", label=path, path=path, line=line))
    return out[:20]


def neighbors_for_path(scan_id: str, path: str) -> dict:
    deps = load_artifact(scan_id, "dependencies.json")
    if not deps:
        return {"imports": [], "imported_by": []}
    imports = []
    imported_by = []
    for e in deps.get("edges") or []:
        if e.get("source") == path:
            imports.append(e.get("target"))
        if e.get("target") == path:
            imported_by.append(e.get("source"))
    return {"path": path, "imports": imports, "imported_by": imported_by}
