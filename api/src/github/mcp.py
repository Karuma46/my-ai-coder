from typing import Any

from fastmcp import FastMCP

from src.github.config import get_github_settings
from src.github.schemas import (
    BranchCreate,
    IssueClose,
    IssueCreate,
    PullRequestCreate,
    PullRequestMerge,
    ReleaseTrigger,
)
from src.github.service import GithubService

mcp = FastMCP(
    "Project Release GitHub Gateway",
    instructions=(
        "Use these curated GitHub tools only for repositories approved by the application. "
        "Merging and releasing require separate server-side feature gates."
    ),
    mask_error_details=True,
)


def get_service() -> GithubService:
    return GithubService(get_github_settings())


@mcp.tool
async def github_create_issue(
    repo: str,
    title: str,
    description: str = "",
    labels: list[str] | None = None,
) -> Any:
    """Create an issue in an approved repository."""
    return await get_service().create_issue(
        IssueCreate(
            repo=repo,
            title=title,
            description=description,
            labels=labels or [],
        )
    )


@mcp.tool
async def github_close_issue(
    repo: str,
    issue_number: int,
) -> Any:
    """Close a completed issue in an approved repository."""
    return await get_service().close_issue(IssueClose(repo=repo, issue_number=issue_number))


@mcp.tool
async def github_create_branch(
    repo: str,
    branch: str,
    from_branch: str | None = None,
) -> Any:
    """Create a branch in an approved repository."""
    return await get_service().create_branch(
        BranchCreate(repo=repo, branch=branch, from_branch=from_branch)
    )


@mcp.tool
async def github_create_pull_request(
    repo: str,
    title: str,
    head: str,
    base: str = "main",
    description: str = "",
    draft: bool = True,
) -> Any:
    """Create a pull request in an approved repository."""
    return await get_service().create_pull_request(
        PullRequestCreate(
            repo=repo,
            title=title,
            head=head,
            base=base,
            description=description,
            draft=draft,
        )
    )


@mcp.tool
async def github_merge_pull_request(
    repo: str,
    pull_number: int,
    merge_method: str = "squash",
) -> Any:
    """Merge a pull request when the server-side merge gate is enabled."""
    return await get_service().merge_pull_request(
        PullRequestMerge(
            repo=repo,
            pull_number=pull_number,
            merge_method=merge_method,
        )
    )


@mcp.tool
async def github_trigger_release(
    repo: str,
    version: str,
    workflow_id: str = "release.yml",
    ref: str = "main",
    prerelease: bool = False,
) -> Any:
    """Trigger an approved repository's release workflow."""
    return await get_service().trigger_release(
        ReleaseTrigger(
            repo=repo,
            version=version,
            workflow_id=workflow_id,
            ref=ref,
            prerelease=prerelease,
        )
    )
