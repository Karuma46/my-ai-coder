from types import SimpleNamespace

import pytest

from src.github.exceptions import GithubUpstreamError
from src.projects.schemas import MergeTodoRequest, TodoStatus
from src.projects.service import ProjectService


async def test_merge_retry_closes_issue_without_merging_pull_request_twice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    project = SimpleNamespace(repository_slug="approved-repo")
    todo = SimpleNamespace(
        version=SimpleNamespace(branch_name="version/v1"),
        status=TodoStatus.DONE,
        is_merged=False,
        pull_request_number=17,
        issue_number=42,
        merge_commit_sha=None,
        merged_at=None,
        updated_at=None,
    )

    class FakeGithub:
        close_attempts = 0

        async def merge_pull_request(self, payload):
            events.append(f"merge:{payload.pull_number}")
            return {"merged": True, "sha": "a" * 40}

        async def close_issue(self, payload):
            self.close_attempts += 1
            events.append(f"close:{payload.issue_number}")
            if self.close_attempts == 1:
                raise GithubUpstreamError("temporary close failure")
            return {"number": payload.issue_number, "state": "closed"}

    service = ProjectService(None, FakeGithub(), "user")

    async def fake_get_project(project_id: str):
        return project

    async def fake_get_todo(project_id: str, todo_id: str):
        return todo

    async def fake_ensure_todo_pull_request(current_project, current_todo, version):
        return None

    async def fake_commit():
        events.append("commit")

    monkeypatch.setattr(service, "get_project", fake_get_project)
    monkeypatch.setattr(service, "get_todo", fake_get_todo)
    monkeypatch.setattr(
        service,
        "_ensure_todo_pull_request",
        fake_ensure_todo_pull_request,
    )
    monkeypatch.setattr(service, "_commit", fake_commit)

    with pytest.raises(GithubUpstreamError):
        await service.merge_todo("project", "todo", MergeTodoRequest())

    assert todo.is_merged is True
    assert events == ["merge:17", "commit", "close:42"]

    result = await service.merge_todo("project", "todo", MergeTodoRequest())

    assert result is todo
    assert events == ["merge:17", "commit", "close:42", "close:42"]
