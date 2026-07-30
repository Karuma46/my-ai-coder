from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from src.accounts.dependencies import CurrentUser
from src.agents.config import AgentSettings, get_agent_settings
from src.agents.runner import LocalAgentRunner
from src.agents.service import AgentRunService
from src.database import DatabaseSession
from src.github.dependencies import GithubServiceDep


@lru_cache
def get_agent_runner() -> LocalAgentRunner:
    return LocalAgentRunner(get_agent_settings())


async def get_agent_run_service(
    session: DatabaseSession,
    github: GithubServiceDep,
    settings: Annotated[AgentSettings, Depends(get_agent_settings)],
    runner: Annotated[LocalAgentRunner, Depends(get_agent_runner)],
    user: CurrentUser,
) -> AgentRunService:
    return AgentRunService(session, runner, settings, github, user.id)


AgentRunServiceDep = Annotated[AgentRunService, Depends(get_agent_run_service)]
