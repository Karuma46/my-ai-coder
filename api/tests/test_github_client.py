import logging
from types import TracebackType
from typing import Self

import pytest

from src.github import client as github_client
from src.github.config import GithubSettings
from src.github.exceptions import GithubUpstreamError


class FailingClient:
    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    async def call_tool(self, tool_name: str, arguments: dict[str, object]) -> None:
        raise RuntimeError(
            "GitHub rejected the branch because the base reference was not found; "
            "token=github_pat_secretvalue"
        )


async def test_upstream_error_is_logged_exposed_and_redacted(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    settings = GithubSettings(
        enabled=True,
        owner="example",
        personal_access_token="github_pat_secretvalue",
    )
    monkeypatch.setattr(
        github_client,
        "create_github_client",
        lambda configured_settings: FailingClient(),
    )

    with (
        caplog.at_level(logging.ERROR, logger="uvicorn.error"),
        pytest.raises(GithubUpstreamError) as error,
    ):
        await github_client.call_github_tool(
            settings,
            "create_branch",
            {"repo": "example-repo", "branch": "version/v1"},
        )

    message = str(error.value)
    assert "base reference was not found" in message
    assert "github_pat_secretvalue" not in message
    assert "[REDACTED]" in message
    assert "create_branch" in caplog.text
    assert "base reference was not found" in caplog.text
    assert "github_pat_secretvalue" not in caplog.text
