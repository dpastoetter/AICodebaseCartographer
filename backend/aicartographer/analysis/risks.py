"""Heuristic security / danger checks for a scanned repository.

This intentionally stays lightweight and offline:
- No dependency CVE feeds (can be added later as an optional plugin)
- Best-effort regex/pattern matching on source/config files

The goal is to surface suspicious hotspots quickly, not to be a full SAST tool.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from ..models import RiskFinding, RisksReport, RiskSeverity
from ..parsers.treesitter import ParsedFile
from ..walker import WalkResult


@dataclass(frozen=True)
class _Rule:
    id: str
    severity: RiskSeverity
    kind: str
    title: str
    pattern: re.Pattern[str]
    detail: str


def _rid(*parts: object) -> str:
    h = hashlib.sha1()
    for p in parts:
        h.update(str(p).encode("utf-8", errors="ignore"))
        h.update(b"\0")
    return h.hexdigest()[:12]


_SECRET_RULES: list[_Rule] = [
    _Rule(
        id="secret.aws_access_key_id",
        severity="high",
        kind="secret",
        title="Possible AWS access key id",
        pattern=re.compile(r"(?<![A-Z0-9])(AKIA|ASIA)[A-Z0-9]{16}(?![A-Z0-9])"),
        detail="Looks like an AWS access key id. If this is real, rotate it and remove from git history.",
    ),
    _Rule(
        id="secret.generic_api_key",
        severity="medium",
        kind="secret",
        title="Possible API key / token assignment",
        pattern=re.compile(
            r"(?i)\b(api[_-]?key|token|secret|password|passwd)\b\s*[:=]\s*[\"'][^\"']{12,}[\"']"
        ),
        detail="Looks like a hardcoded credential. Prefer env vars / secret managers.",
    ),
    _Rule(
        id="secret.private_key_block",
        severity="critical",
        kind="secret",
        title="Private key material in repository",
        pattern=re.compile(r"-----BEGIN (?:RSA|EC|DSA|OPENSSH|ED25519) PRIVATE KEY-----"),
        detail="Private key material detected. Remove immediately and rotate associated credentials.",
    ),
]

_DANGER_RULES: list[_Rule] = [
    _Rule(
        id="danger.python_eval_exec",
        severity="high",
        kind="insecure_api",
        title="Dynamic code execution (eval/exec)",
        pattern=re.compile(r"(?m)\b(eval|exec)\s*\("),
        detail="Dynamic execution can lead to RCE if inputs are attacker-controlled.",
    ),
    _Rule(
        id="danger.python_subprocess_shell",
        severity="high",
        kind="insecure_api",
        title="subprocess with shell=True",
        pattern=re.compile(r"(?m)\bshell\s*=\s*True\b"),
        detail="shell=True is high risk with untrusted inputs.",
    ),
    _Rule(
        id="danger.python_pickle",
        severity="high",
        kind="insecure_api",
        title="Pickle deserialization",
        pattern=re.compile(r"(?m)\b(pickle\.loads|pickle\.load)\s*\("),
        detail="Untrusted pickle data can lead to arbitrary code execution.",
    ),
    _Rule(
        id="danger.yaml_load",
        severity="medium",
        kind="insecure_api",
        title="Potentially unsafe yaml.load",
        pattern=re.compile(r"(?m)\byaml\.load\s*\("),
        detail="Prefer yaml.safe_load unless you control all inputs.",
    ),
    _Rule(
        id="danger.requests_verify_false",
        severity="high",
        kind="insecure_config",
        title="TLS verification disabled (verify=False)",
        pattern=re.compile(r"(?m)\bverify\s*=\s*False\b"),
        detail="Disabling TLS verification enables MITM attacks.",
    ),
    _Rule(
        id="danger.weak_hash",
        severity="low",
        kind="note",
        title="Weak hash function usage (md5/sha1)",
        pattern=re.compile(r"(?m)\b(hashlib\.(md5|sha1)|\bmd5\s*\(|\bsha1\s*\()"),
        detail="MD5/SHA1 are collision-prone. Prefer SHA-256+ for integrity and modern password hashing for credentials.",
    ),
]


_SKIP_EXTS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".bz2",
    ".xz",
    ".7z",
}


def build(root: Path, walk: WalkResult, parsed: list[ParsedFile]) -> RisksReport:
    """Compute a heuristic 'danger' report."""
    report = RisksReport()

    # Scan text-like files from the walker; this includes configs where risks often live.
    for f in walk.files:
        p = f.abs_path
        if p.suffix.lower() in _SKIP_EXTS:
            continue
        try:
            text = p.read_text(errors="ignore")
        except OSError:
            continue
        _apply_rules(report, f.rel_path, text)

    # Add a few meta findings for common misconfigurations we can infer quickly.
    _infer_repo_level_risks(report, root)

    # Stable sort: severity then kind then path
    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    report.findings.sort(
        key=lambda x: (sev_order.get(x.severity, 9), x.kind, x.path or "", x.line or 0, x.title)
    )
    return report


def _apply_rules(report: RisksReport, rel_path: str, text: str) -> None:
    rules = _SECRET_RULES + _DANGER_RULES
    for rule in rules:
        for m in rule.pattern.finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            report.findings.append(
                RiskFinding(
                    id=_rid(rule.id, rel_path, line, rule.title),
                    severity=rule.severity,
                    kind=rule.kind,  # type: ignore[arg-type]
                    title=rule.title,
                    detail=rule.detail,
                    path=rel_path,
                    line=line,
                    rule=rule.id,
                )
            )


def _infer_repo_level_risks(report: RisksReport, root: Path) -> None:
    # If .env is present, remind users to ensure it is ignored (we don't read it here).
    env_file = root / ".env"
    if env_file.exists():
        report.findings.append(
            RiskFinding(
                id=_rid("note.env_present", root),
                severity="low",
                kind="note",
                title="A .env file exists at repo root",
                detail="Ensure .env is gitignored and never committed. Prefer per-environment secret management.",
                path=".env",
                line=None,
                rule="note.env_present",
            )
        )

