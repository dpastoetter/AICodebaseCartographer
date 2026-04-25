"""Disk-backed cache for LLM responses, keyed by content hash."""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

from ..models import ModuleCard
from ..storage import llm_cache_root

log = logging.getLogger(__name__)


def _key(provider: str, model: str, path: str, code: str, prompt_version: str) -> str:
    h = hashlib.sha256()
    h.update(provider.encode())
    h.update(b"|")
    h.update(model.encode())
    h.update(b"|")
    h.update(prompt_version.encode())
    h.update(b"|")
    h.update(path.encode())
    h.update(b"|")
    h.update(code.encode("utf-8", errors="replace"))
    return h.hexdigest()


def _path_for(key: str) -> Path:
    sub = llm_cache_root() / key[:2]
    sub.mkdir(parents=True, exist_ok=True)
    return sub / f"{key}.json"


def get(provider: str, model: str, path: str, code: str, prompt_version: str) -> ModuleCard | None:
    p = _path_for(_key(provider, model, path, code, prompt_version))
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text())
        return ModuleCard.model_validate(data)
    except Exception as exc:  # noqa: BLE001
        log.debug("cache read failed for %s: %s", p, exc)
        return None


def put(provider: str, model: str, path: str, code: str, prompt_version: str, card: ModuleCard) -> None:
    p = _path_for(_key(provider, model, path, code, prompt_version))
    try:
        p.write_text(card.model_dump_json())
    except OSError as exc:
        log.debug("cache write failed for %s: %s", p, exc)
