"""Encrypted local secret storage for API keys.

Secrets are stored locally under AICARTOGRAPHER_HOME and never returned via API.
"""

from __future__ import annotations

import contextlib
import os
from pathlib import Path

from cryptography.fernet import Fernet

from .storage import data_root

_PROVIDERS = {"openai", "anthropic"}


class SecretsError(RuntimeError):
    pass


def secrets_root() -> Path:
    root = data_root() / "secrets"
    root.mkdir(parents=True, exist_ok=True)
    return root


def configured() -> dict[str, bool]:
    root = secrets_root()
    return {p: (root / f"{p}.enc").exists() for p in sorted(_PROVIDERS)}


def set_key(provider: str, api_key: str) -> None:
    provider = _validate_provider(provider)
    api_key = (api_key or "").strip()
    if not api_key:
        raise SecretsError("Empty API key.")
    token = _fernet().encrypt(api_key.encode("utf-8"))
    p = secrets_root() / f"{provider}.enc"
    p.write_bytes(token)
    _chmod_600(p)


def clear_key(provider: str) -> None:
    provider = _validate_provider(provider)
    p = secrets_root() / f"{provider}.enc"
    if p.exists():
        p.unlink()


def get_key(provider: str) -> str | None:
    provider = _validate_provider(provider)
    p = secrets_root() / f"{provider}.enc"
    if not p.exists():
        return None
    try:
        token = p.read_bytes()
        return _fernet().decrypt(token).decode("utf-8")
    except Exception as exc:  # noqa: BLE001
        raise SecretsError(f"Failed to decrypt {provider} key.") from exc


def _validate_provider(provider: str) -> str:
    p = (provider or "").strip().lower()
    if p not in _PROVIDERS:
        raise SecretsError(f"Unknown provider: {provider}")
    return p


def _fernet() -> Fernet:
    key_path = secrets_root() / "master.key"
    if not key_path.exists():
        key = Fernet.generate_key()
        key_path.write_bytes(key)
        _chmod_600(key_path)
    else:
        key = key_path.read_bytes()
    return Fernet(key)


def _chmod_600(path: Path) -> None:
    if os.name != "posix":
        return
    with contextlib.suppress(OSError):
        os.chmod(path, 0o600)

