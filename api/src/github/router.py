from typing import Any

from fastapi import APIRouter, status

from src.github.dependencies import GithubServiceDep
from src.github.schemas import (
    BranchCreate,
    IssueCreate,
    PullRequestCreate,
    PullRequestMerge,
    ReleaseTrigger,
)

router = APIRouter(prefix="/github", tags=["github"])


@router.get("/tools", summary="List enabled upstream GitHub MCP tools")
async def list_tools(service: GithubServiceDep) -> list[Any]:
    return await service.list_tools()


@router.post(
    "/issues",
    status_code=status.HTTP_201_CREATED,
    summary="Create a GitHub issue",
)
async def create_issue(payload: IssueCreate, service: GithubServiceDep) -> Any:
    return await service.create_issue(payload)


@router.post(
    "/branches",
    status_code=status.HTTP_201_CREATED,
    summary="Create a GitHub branch",
)
async def create_branch(payload: BranchCreate, service: GithubServiceDep) -> Any:
    return await service.create_branch(payload)


@router.post(
    "/pull-requests",
    status_code=status.HTTP_201_CREATED,
    summary="Create a GitHub pull request",
)
async def create_pull_request(payload: PullRequestCreate, service: GithubServiceDep) -> Any:
    return await service.create_pull_request(payload)


@router.post("/pull-requests/merge", summary="Merge a GitHub pull request")
async def merge_pull_request(payload: PullRequestMerge, service: GithubServiceDep) -> Any:
    return await service.merge_pull_request(payload)


@router.post(
    "/releases", status_code=status.HTTP_202_ACCEPTED, summary="Trigger a release workflow"
)
async def trigger_release(payload: ReleaseTrigger, service: GithubServiceDep) -> Any:
    return await service.trigger_release(payload)
