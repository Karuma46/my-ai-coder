from typing import Annotated

from fastapi import Depends

from src.github.config import GithubSettings, get_github_settings
from src.github.service import GithubService


async def get_github_service(
    settings: Annotated[GithubSettings, Depends(get_github_settings)],
) -> GithubService:
    return GithubService(settings)


GithubServiceDep = Annotated[GithubService, Depends(get_github_service)]
