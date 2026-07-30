from typing import Literal

from pydantic import BaseModel, Field

REPOSITORY_PATTERN = r"^[A-Za-z0-9_.-]+$"
BRANCH_PATTERN = r"^[A-Za-z0-9._/-]+$"


class IssueCreate(BaseModel):
    repo: str = Field(min_length=1, max_length=100, pattern=REPOSITORY_PATTERN)
    title: str = Field(min_length=3, max_length=256)
    description: str = Field(default="", max_length=65_536)
    labels: list[str] = Field(default_factory=list, max_length=20)


class IssueClose(BaseModel):
    repo: str = Field(min_length=1, max_length=100, pattern=REPOSITORY_PATTERN)
    issue_number: int = Field(gt=0)


class BranchCreate(BaseModel):
    repo: str = Field(min_length=1, max_length=100, pattern=REPOSITORY_PATTERN)
    branch: str = Field(min_length=1, max_length=255, pattern=BRANCH_PATTERN)
    from_branch: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        pattern=BRANCH_PATTERN,
    )


class PullRequestCreate(BaseModel):
    repo: str = Field(min_length=1, max_length=100, pattern=REPOSITORY_PATTERN)
    title: str = Field(min_length=3, max_length=256)
    head: str = Field(min_length=1, max_length=255, pattern=BRANCH_PATTERN)
    base: str = Field(default="main", min_length=1, max_length=255, pattern=BRANCH_PATTERN)
    description: str = Field(default="", max_length=65_536)
    draft: bool = True


class PullRequestMerge(BaseModel):
    repo: str = Field(min_length=1, max_length=100, pattern=REPOSITORY_PATTERN)
    pull_number: int = Field(gt=0)
    merge_method: Literal["merge", "squash", "rebase"] = "squash"
    commit_title: str | None = Field(default=None, max_length=256)
    commit_message: str | None = Field(default=None, max_length=65_536)


class ReleaseTrigger(BaseModel):
    repo: str = Field(min_length=1, max_length=100, pattern=REPOSITORY_PATTERN)
    version: str = Field(min_length=1, max_length=100)
    workflow_id: str = Field(default="release.yml", min_length=1, max_length=255)
    ref: str = Field(default="main", min_length=1, max_length=255, pattern=BRANCH_PATTERN)
    prerelease: bool = False
