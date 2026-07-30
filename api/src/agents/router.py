import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Path,
    Query,
    Response,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from redis.exceptions import RedisError

from src.accounts.config import AuthSettings, get_auth_settings
from src.accounts.exceptions import AuthenticationError
from src.accounts.models import CompanyMembership
from src.accounts.security import decode_access_token
from src.agents.dependencies import AgentRunServiceDep
from src.agents.events import (
    AgentEventBroker,
    AgentRunCompletedEvent,
    get_agent_event_broker,
)
from src.agents.schemas import (
    AgentRunResponse,
    CreateAgentRunRequest,
    CreateLocalAgentRequest,
    LocalAgentResponse,
    UpdateLocalAgentRequest,
)
from src.database import DatabaseSession
from src.projects.models import Project

router = APIRouter(prefix="/api/v1/agent-runs", tags=["Agent runs"])
logger = logging.getLogger(__name__)

RunId = Annotated[str, Path(alias="runId", min_length=1)]
CompanyId = Annotated[str, Path(alias="companyId", min_length=1)]
AgentId = Annotated[str, Path(alias="agentId", min_length=1)]
AgentEventBrokerDep = Annotated[AgentEventBroker, Depends(get_agent_event_broker)]


async def _stream_agent_events(
    websocket: WebSocket,
    events: AsyncIterator[AgentRunCompletedEvent],
    project_id: str | None,
) -> None:
    event_task = asyncio.create_task(anext(events))
    receive_task = asyncio.create_task(websocket.receive())
    try:
        while True:
            done, _ = await asyncio.wait(
                {event_task, receive_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            if receive_task in done:
                message = receive_task.result()
                if message["type"] == "websocket.disconnect":
                    return
                receive_task = asyncio.create_task(websocket.receive())

            if event_task in done:
                try:
                    event = event_task.result()
                except StopAsyncIteration:
                    return
                if project_id is None or event.project_id == project_id:
                    await websocket.send_json(event.model_dump(mode="json", by_alias=True))
                event_task = asyncio.create_task(anext(events))
    finally:
        event_task.cancel()
        receive_task.cancel()
        await asyncio.gather(event_task, receive_task, return_exceptions=True)


@router.post(
    "",
    response_model=AgentRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Run a planned todo with a local coding agent",
    description=(
        "Fetches the todo's stored GitHub branch, checks it out when needed, runs the "
        "selected local coding agent, and records its output."
    ),
)
async def create_agent_run(
    payload: CreateAgentRunRequest,
    service: AgentRunServiceDep,
):
    run = await service.enqueue_planned_todo(payload)
    if await service.is_todo_branch_ready(run.todo_id):
        from src.agents.tasks import execute_agent_run

        execute_agent_run.apply_async(args=[run.id])
    return run


@router.websocket("/events")
async def agent_run_events(
    websocket: WebSocket,
    broker: AgentEventBrokerDep,
    session: DatabaseSession,
    settings: Annotated[AuthSettings, Depends(get_auth_settings)],
    project_id: str = Query(alias="projectId", min_length=1),
    token: str = Query(min_length=1),
) -> None:
    try:
        user_id = decode_access_token(token, settings)
    except AuthenticationError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    project = await session.get(Project, project_id)
    membership = (
        await session.get(CompanyMembership, (project.company_id, user_id))
        if project is not None
        else None
    )
    if membership is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await websocket.accept()
    try:
        async with broker.subscribe() as events:
            await _stream_agent_events(websocket, events, project_id)
    except WebSocketDisconnect:
        return
    except RedisError:
        logger.exception("Task event WebSocket lost its Redis subscription")
        await websocket.close(
            code=status.WS_1011_INTERNAL_ERROR,
            reason="Task event service is unavailable",
        )


@router.get(
    "/{runId}",
    response_model=AgentRunResponse,
    summary="Get a local agent run",
)
async def get_agent_run(run_id: RunId, service: AgentRunServiceDep):
    return await service.get_run(run_id)


@router.get(
    "/companies/{companyId}/local-agents",
    response_model=list[LocalAgentResponse],
    summary="List a company's local agents",
)
async def list_local_agents(company_id: CompanyId, service: AgentRunServiceDep):
    return await service.list_local_agents(company_id)


@router.post(
    "/companies/{companyId}/local-agents",
    response_model=LocalAgentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a local agent",
)
async def create_local_agent(
    company_id: CompanyId,
    payload: CreateLocalAgentRequest,
    service: AgentRunServiceDep,
):
    return await service.create_local_agent(company_id, payload)


@router.patch(
    "/companies/{companyId}/local-agents/{agentId}",
    response_model=LocalAgentResponse,
    summary="Update a local agent",
)
async def update_local_agent(
    company_id: CompanyId,
    agent_id: AgentId,
    payload: UpdateLocalAgentRequest,
    service: AgentRunServiceDep,
):
    return await service.update_local_agent(company_id, agent_id, payload)


@router.delete(
    "/companies/{companyId}/local-agents/{agentId}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a local agent",
)
async def delete_local_agent(
    company_id: CompanyId,
    agent_id: AgentId,
    service: AgentRunServiceDep,
) -> Response:
    await service.delete_local_agent(company_id, agent_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
