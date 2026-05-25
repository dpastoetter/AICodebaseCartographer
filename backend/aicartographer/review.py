"""PR review: scan two git refs and compare artifacts."""
from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from .compare import compare_scans
from .github import RepoCloneError, RepoParseError, ensure_cloned, parse_repo
from .models import ScanCompareResult, ScanRequest, ScanReviewRequest, ScanReviewResult
from .scanner import registry, run_scan_sync

log = logging.getLogger(__name__)


def _resolve_repo_path(repo: str) -> Path:
    p = Path(repo).expanduser()
    if p.is_dir() and (p / ".git").exists():
        return p.resolve()
    ref = parse_repo(repo)
    return ensure_cloned(ref)


def _checkout_worktree(repo: Path, git_ref: str) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="aicarto-review-"))
    try:
        rev = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--verify", git_ref],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        subprocess.run(
            ["git", "-C", str(repo), "worktree", "add", "--detach", str(tmp), rev],
            check=True,
            capture_output=True,
            text=True,
        )
        return tmp
    except subprocess.CalledProcessError as exc:
        shutil.rmtree(tmp, ignore_errors=True)
        stderr = (exc.stderr or "").strip() if hasattr(exc, "stderr") else str(exc)
        raise RepoCloneError(f"Cannot checkout {git_ref}: {stderr}") from exc


def _cleanup_worktree(repo: Path, wt: Path) -> None:
    with subprocess.Popen(
        ["git", "-C", str(repo), "worktree", "remove", "--force", str(wt)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ):
        pass
    shutil.rmtree(wt, ignore_errors=True)


def _scan_path(path: Path, req: ScanReviewRequest) -> str:
    scan_req = ScanRequest(
        path=str(path),
        llm=req.llm,
        model=req.model,
        max_files=req.max_files,
    )
    record = registry.create(scan_req)
    run_scan_sync(record, scan_req)
    return record.status.scan_id


def _summary(compare: ScanCompareResult) -> str:
    parts = [
        f"{len(compare.files_added)} files added, {len(compare.files_removed)} removed",
        f"{len(compare.risks_added)} new risks, {len(compare.risks_removed)} risks removed",
        f"{len(compare.vulns_added)} new CVEs, {len(compare.vulns_removed)} CVEs resolved",
        f"{len(compare.deps_added)} new dependency edges",
    ]
    return "; ".join(parts)


def run_review(req: ScanReviewRequest) -> ScanReviewResult:
    try:
        repo_path = _resolve_repo_path(req.repo)
    except RepoParseError as exc:
        raise ValueError(str(exc)) from exc
    except RepoCloneError as exc:
        raise ValueError(str(exc)) from exc

    base_wt = _checkout_worktree(repo_path, req.base)
    head_wt = _checkout_worktree(repo_path, req.head)
    try:
        scan_base = _scan_path(base_wt, req)
        scan_head = _scan_path(head_wt, req)
        compare = compare_scans(scan_base, scan_head)
        return ScanReviewResult(
            scan_base=scan_base,
            scan_head=scan_head,
            compare=compare,
            summary=_summary(compare),
        )
    finally:
        _cleanup_worktree(repo_path, base_wt)
        _cleanup_worktree(repo_path, head_wt)
