import pytest

from src.github import client as github_client
from src.github.config import GithubSettings
from src.github.exceptions import (
    GithubOperationDisabledError,
    GithubRepositoryNotAllowedError,
)
from src.github.schemas import IssueClose, IssueCreate
from src.github.service import GithubService


async def test_repository_must_be_allowed() -> None:
    service = GithubService(
        GithubSettings(
            enabled=True,
            owner="example",
            allowed_repositories="approved-repo",
            write_enabled=True,
        )
    )

    with pytest.raises(GithubRepositoryNotAllowedError):
        await service.create_issue(
            IssueCreate(repo="other-repo", title="This repository is not approved")
        )


async def test_writes_are_disabled_separately() -> None:
    service = GithubService(
        GithubSettings(
            enabled=True,
            owner="example",
            allowed_repositories="approved-repo",
            write_enabled=False,
        )
    )

    with pytest.raises(GithubOperationDisabledError):
        await service.create_issue(IssueCreate(repo="approved-repo", title="This write is gated"))


async def test_close_issue_uses_issue_write_update(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    async def fake_call_github_tool(settings, tool_name, arguments):
        calls.append((tool_name, arguments))
        return {"number": arguments["issue_number"], "state": arguments["state"]}

    monkeypatch.setattr(github_client, "call_github_tool", fake_call_github_tool)
    service = GithubService(
        GithubSettings(
            enabled=True,
            owner="example",
            allowed_repositories="approved-repo",
            write_enabled=True,
        )
    )

    result = await service.close_issue(IssueClose(repo="approved-repo", issue_number=42))

    assert result == {"number": 42, "state": "closed"}
    assert calls == [
        (
            "issue_write",
            {
                "method": "update",
                "owner": "example",
                "repo": "approved-repo",
                "issue_number": 42,
                "state": "closed",
                "state_reason": "completed",
            },
        )
    ]
