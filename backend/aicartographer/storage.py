"""On-disk locations for scan snapshots and the LLM cache."""
from __future__ import annotations

import os
from pathlib import Path


def _data_root() -> Path:
    override = os.environ.get("AICARTOGRAPHER_HOME")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".aicartographer"


def data_root() -> Path:
    root = _data_root()
    root.mkdir(parents=True, exist_ok=True)
    return root


def scans_root() -> Path:
    root = data_root() / "scans"
    root.mkdir(parents=True, exist_ok=True)
    return root


def scan_dir(scan_id: str) -> Path:
    p = scans_root() / scan_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def llm_cache_root() -> Path:
    root = data_root() / "llm-cache"
    root.mkdir(parents=True, exist_ok=True)
    return root


def clones_root() -> Path:
    root = data_root() / "clones"
    root.mkdir(parents=True, exist_ok=True)
    return root
