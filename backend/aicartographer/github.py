"""Utilities for cloning and updating public GitHub repositories.

Public repos only (no authentication). Clones are stored under the app data
root so that repeated scans are fast.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from .storage import clones_root

_OWNER_REPO = re.compile(r"^(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+?)(?:\\.git)?$")


@dataclass(frozen=True)
class RepoRef:
    owner: str
    repo: str

    @property
    def slug(self) -> str:
        return f"{self.owner}/{self.repo}"

    @property
    def https_url(self) -> str:
        return f"https://github.com/{self.owner}/{self.repo}.git"

    @property
    def local_path(self) -> Path:
        return clones_root() / self.owner / self.repo


class RepoParseError(ValueError):
    pass


class RepoCloneError(RuntimeError):
    pass


def parse_repo(value: str) -> RepoRef:
    """Parse a repo identifier into owner/repo.

    Accepted forms:
    - owner/repo
    - https://github.com/owner/repo
    - https://github.com/owner/repo.git
    - git@github.com:owner/repo.git
    """
    raw = value.strip()
    if not raw:
        raise RepoParseError("Repo is empty")

    # owner/repo
    m = _OWNER_REPO.match(raw)
    if m:
        repo = m.group("repo")
        if repo.endswith(".git"):
            repo = repo.removesuffix(".git")
        return RepoRef(owner=m.group("owner"), repo=repo)

    # git@github.com:owner/repo(.git)
    if raw.startswith("git@"):
        try:
            _user_host, path = raw.split(":", 1)
        except ValueError as exc:
            raise RepoParseError("Invalid SSH repo form") from exc
        if not raw.startswith("git@github.com:"):
            raise RepoParseError("Only github.com is supported")
        m = _OWNER_REPO.match(path)
        if not m:
            raise RepoParseError("Invalid GitHub repo path")
        repo = m.group("repo")
        if repo.endswith(".git"):
            repo = repo.removesuffix(".git")
        return RepoRef(owner=m.group("owner"), repo=repo)

    # https URL
    if raw.startswith("http://") or raw.startswith("https://"):
        u = urlparse(raw)
        if u.netloc not in {"github.com", "www.github.com"}:
            raise RepoParseError("Only github.com is supported")
        path = (u.path or "").lstrip("/")
        m = _OWNER_REPO.match(path)
        if not m:
            raise RepoParseError("Expected https://github.com/<owner>/<repo>")
        repo = m.group("repo")
        if repo.endswith(".git"):
            repo = repo.removesuffix(".git")
        return RepoRef(owner=m.group("owner"), repo=repo)

    raise RepoParseError("Unsupported repo format. Use owner/repo or a GitHub URL.")


def ensure_cloned(repo: RepoRef, *, timeout_s: int = 180) -> Path:
    """Clone or update the repository and return the local path."""
    path = repo.local_path
    path.parent.mkdir(parents=True, exist_ok=True)

    if not path.exists():
        _run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "--",
                repo.https_url,
                str(path),
            ],
            timeout_s=timeout_s,
        )
        return path

    # Existing clone: bring it to origin/HEAD (depth=1 for speed).
    _run(["git", "-C", str(path), "fetch", "--depth", "1", "origin"], timeout_s=timeout_s)
    _run(["git", "-C", str(path), "reset", "--hard", "origin/HEAD"], timeout_s=timeout_s)
    return path


def _run(args: list[str], *, timeout_s: int) -> None:
    try:
        subprocess.run(
            args,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as exc:
        raise RepoCloneError(f"git timed out: {' '.join(args)}") from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        msg = stderr.splitlines()[-1] if stderr else "git failed"
        raise RepoCloneError(msg) from exc

