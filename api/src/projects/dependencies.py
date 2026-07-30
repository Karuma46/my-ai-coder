from typing import Annotated

from fastapi import Depends

from src.accounts.dependencies import CurrentUser
from src.database import DatabaseSession
from src.github.dependencies import GithubServiceDep
from src.projects.service import ProjectService


async def get_project_service(
    session: DatabaseSession,
    github: GithubServiceDep,
    user: CurrentUser,
) -> ProjectService:
    return ProjectService(session, github, user.id)


ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]
