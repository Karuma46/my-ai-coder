from dataclasses import asdict, is_dataclass
from typing import Any

from src.github import client as github_client
from src.github.config import GithubSettings
from src.github.exceptions import (
    GithubOperationDisabledError,
    GithubRepositoryNotAllowedError,
)
from src.github.schemas import (
    BranchCreate,
    IssueClose,
    IssueCreate,
    PullRequestCreate,
    PullRequestMerge,
    ReleaseTrigger,
)


def serialize_result(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return serialize_result(value.model_dump(mode="json"))
    if is_dataclass(value) and not isinstance(value, type):
        return serialize_result(asdict(value))
    if isinstance(value, dict):
        return {key: serialize_result(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [serialize_result(item) for item in value]
    return value


class GithubService:
    def __init__(self, settings: GithubSettings) -> None:
        self.settings = settings

    def validate_repository(self, repository: str) -> None:
        allowed = self.settings.allowed_repository_names
        if not allowed:
            raise GithubRepositoryNotAllowedError(
                "No GitHub repositories have been added to the allow-list"
            )
        if repository not in allowed:
            raise GithubRepositoryNotAllowedError(
                f"Repository '{repository}' is not in the GitHub allow-list"
            )

    def require_write_access(self) -> None:
        if not self.settings.write_enabled:
            raise GithubOperationDisabledError("GitHub write operations are disabled")

    async def list_tools(self) -> list[Any]:
        tools = await github_client.list_github_tools(self.settings)
        return serialize_result(tools)

    async def create_issue(self, payload: IssueCreate) -> Any:
        self.validate_repository(payload.repo)
        self.require_write_access()
        return await self._call(
            "issue_write",
            {
                "method": "create",
                "owner": self.settings.owner,
                "repo": payload.repo,
                "title": payload.title,
                "body": payload.description,
                "labels": payload.labels,
            },
        )

    async def close_issue(self, payload: IssueClose) -> Any:
        self.validate_repository(payload.repo)
        self.require_write_access()
        return await self._call(
            "issue_write",
            {
                "method": "update",
                "owner": self.settings.owner,
                "repo": payload.repo,
                "issue_number": payload.issue_number,
                "state": "closed",
                "state_reason": "completed",
            },
        )

    async def create_branch(self, payload: BranchCreate) -> Any:
        self.validate_repository(payload.repo)
        self.require_write_access()
        arguments = {
            "owner": self.settings.owner,
            "repo": payload.repo,
            "branch": payload.branch,
        }
        if payload.from_branch is not None:
            arguments["from_branch"] = payload.from_branch
        return await self._call("create_branch", arguments)

    async def create_pull_request(self, payload: PullRequestCreate) -> Any:
        self.validate_repository(payload.repo)
        self.require_write_access()
        return await self._call(
            "create_pull_request",
            {
                "owner": self.settings.owner,
                "repo": payload.repo,
                "title": payload.title,
                "head": payload.head,
                "base": payload.base,
                "body": payload.description,
                "draft": payload.draft,
            },
        )

    async def merge_pull_request(self, payload: PullRequestMerge) -> Any:
        self.validate_repository(payload.repo)
        self.require_write_access()
        if not self.settings.merge_enabled:
            raise GithubOperationDisabledError("GitHub pull request merging is disabled")

        arguments: dict[str, Any] = {
            "owner": self.settings.owner,
            "repo": payload.repo,
            "pullNumber": payload.pull_number,
            "merge_method": payload.merge_method,
        }
        if payload.commit_title is not None:
            arguments["commit_title"] = payload.commit_title
        if payload.commit_message is not None:
            arguments["commit_message"] = payload.commit_message
        return await self._call("merge_pull_request", arguments)

    async def trigger_release(self, payload: ReleaseTrigger) -> Any:
        self.validate_repository(payload.repo)
        self.require_write_access()
        if not self.settings.release_enabled:
            raise GithubOperationDisabledError("GitHub release workflow triggering is disabled")

        return await self._call(
            "actions_run_trigger",
            {
                "method": "run_workflow",
                "owner": self.settings.owner,
                "repo": payload.repo,
                "workflow_id": payload.workflow_id,
                "ref": payload.ref,
                "inputs": {
                    "version": payload.version,
                    "prerelease": str(payload.prerelease).lower(),
                },
            },
        )

    async def _call(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        result = await github_client.call_github_tool(self.settings, tool_name, arguments)
        return serialize_result(result)
