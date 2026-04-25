from __future__ import annotations

import pytest


def test_parse_repo_owner_repo():
    from aicartographer.github import parse_repo

    r = parse_repo("octocat/Hello-World")
    assert r.owner == "octocat"
    assert r.repo == "Hello-World"
    assert r.slug == "octocat/Hello-World"


def test_parse_repo_https_url():
    from aicartographer.github import parse_repo

    r = parse_repo("https://github.com/octocat/Hello-World")
    assert r.slug == "octocat/Hello-World"

    r = parse_repo("https://github.com/octocat/Hello-World.git")
    assert r.slug == "octocat/Hello-World"


def test_parse_repo_ssh_url():
    from aicartographer.github import parse_repo

    r = parse_repo("git@github.com:octocat/Hello-World.git")
    assert r.slug == "octocat/Hello-World"


def test_parse_repo_rejects_non_github():
    from aicartographer.github import RepoParseError, parse_repo

    with pytest.raises(RepoParseError):
        parse_repo("https://gitlab.com/a/b")

