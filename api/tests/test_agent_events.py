import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.accounts.config import AuthSettings, get_auth_settings
from src.accounts.models import Company, CompanyMembership, User
from src.accounts.schemas import CompanyRole
from src.accounts.security import create_access_token
from src.agents.events import AgentRunCompletedEvent, get_agent_event_broker
from src.agents.router import create_agent_run, router
from src.agents.schemas import (
    AgentProvider,
    AgentRunResponse,
    AgentRunStatus,
    CreateAgentRunRequest,
)
from src.database import Base, get_db
from src.projects.models import Project


def completed_event(project_id: str, run_id: str) -> AgentRunCompletedEvent:
    return AgentRunCompletedEvent(
        run_id=run_id,
        project_id=project_id,
        todo_id=f"todo-{run_id}",
        status=AgentRunStatus.SUCCEEDED,
        completed_at=datetime(2026, 7, 28, 12, 0, tzinfo=UTC),
    )


def test_websocket_streams_completion_events_for_selected_project(tmp_path) -> None:
    class FakeBroker:
        @asynccontextmanager
        async def subscribe(self):
            async def events():
                yield completed_event("other-project", "ignored")
                yield completed_event("shoppa", "run-42")
                await asyncio.Future()

            yield events()

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'events.db'}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def prepare_database() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with session_factory() as session:
            session.add_all(
                [
                    User(
                        id="user",
                        name="User",
                        email="user@example.com",
                        password_hash="unused",
                    ),
                    Company(id="company", name="Company"),
                    CompanyMembership(
                        company_id="company",
                        user_id="user",
                        role=CompanyRole.OWNER,
                    ),
                    Project(
                        id="shoppa",
                        company_id="company",
                        name="Shoppa",
                        path="/shoppa",
                        repository_slug="shoppa",
                    ),
                ]
            )
            await session.commit()

    asyncio.run(prepare_database())
    auth_settings = AuthSettings(jwt_secret="websocket-test-secret-at-least-32-bytes")
    token, _ = create_access_token("user", auth_settings)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_agent_event_broker] = FakeBroker
    app.dependency_overrides[get_auth_settings] = lambda: auth_settings
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        with client.websocket_connect(
            f"/api/v1/agent-runs/events?projectId=shoppa&token={token}"
        ) as websocket:
            message = websocket.receive_json()
            websocket.close()
    asyncio.run(engine.dispose())

    assert message == {
        "type": "agent-run.completed",
        "runId": "run-42",
        "projectId": "shoppa",
        "todoId": "todo-run-42",
        "status": "succeeded",
        "completedAt": "2026-07-28T12:00:00Z",
        "error": None,
    }


async def test_direct_agent_run_is_enqueued_without_completion_event() -> None:
    run = AgentRunResponse(
        id="run-direct",
        project_id="shoppa",
        todo_id="todo-direct",
        provider=AgentProvider.CODEX,
        status=AgentRunStatus.QUEUED,
        branch_name="todo/todo-direct",
        repository_path="/repositories/shoppa",
        pushed=False,
        exit_code=None,
        output="",
        error=None,
        started_at=datetime(2026, 7, 28, 11, 0, tzinfo=UTC),
        completed_at=None,
    )

    class FakeService:
        async def enqueue_planned_todo(self, payload):
            return run

        async def is_todo_branch_ready(self, todo_id):
            return False

    result = await create_agent_run(
        CreateAgentRunRequest(project_id="shoppa", todo_id="todo-direct"),
        FakeService(),
    )

    assert result is run
