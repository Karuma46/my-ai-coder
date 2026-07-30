import asyncio
import logging
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from typing import Any

from redis import Redis
from redis.exceptions import LockNotOwnedError, RedisError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.agents.celery_app import celery_app
from src.agents.celery_config import get_celery_settings
from src.agents.config import get_agent_settings
from src.agents.events import AgentRunCompletedEvent, get_agent_event_broker
from src.agents.exceptions import AgentRunConflictError
from src.agents.runner import LocalAgentRunner
from src.agents.schemas import (
    AgentRunResponse,
    AgentRunStatus,
    CreateAgentRunRequest,
)
from src.agents.service import AgentRunService
from src.config import settings as app_settings
from src.github.config import get_github_settings
from src.github.models import GithubWorkflowTask
from src.github.service import GithubService
from src.github.workflow import GithubTaskAction, GithubTaskStatus
from src.projects.models import ProjectTodo, ProjectVersion
from src.projects.schemas import TodoStatus, VersionStatus

logger = logging.getLogger(__name__)


@contextmanager
def agent_execution_lock() -> Iterator[bool]:
    celery_settings = get_celery_settings()
    agent_settings = get_agent_settings()
    redis_client = Redis.from_url(celery_settings.broker_url)
    lock = redis_client.lock(
        celery_settings.agent_execution_lock_key,
        timeout=agent_settings.timeout_seconds + 900,
        blocking=False,
    )
    acquired = False
    try:
        acquired = bool(lock.acquire(blocking=False))
        yield acquired
    finally:
        if acquired:
            try:
                lock.release()
            except LockNotOwnedError:
                logger.warning("Agent execution lock expired before it could be released")
            except RedisError:
                logger.warning(
                    "Redis unavailable while releasing the agent execution lock",
                    exc_info=True,
                )
        redis_client.close()


@asynccontextmanager
async def agent_service() -> AsyncIterator[AgentRunService]:
    engine = create_async_engine(app_settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            yield _build_service(session)
    finally:
        await engine.dispose()


def _build_service(session: AsyncSession) -> AgentRunService:
    agent_settings = get_agent_settings()
    return AgentRunService(
        session,
        LocalAgentRunner(agent_settings),
        agent_settings,
        GithubService(get_github_settings()),
    )


async def claim_planned_todos() -> list[str]:
    celery_settings = get_celery_settings()
    async with agent_service() as service:
        result = await service.session.execute(
            select(ProjectTodo.project_id, ProjectTodo.id)
            .join(ProjectVersion, ProjectVersion.id == ProjectTodo.version_id)
            .where(ProjectTodo.status == TodoStatus.PLANNED)
            .where(ProjectVersion.status.in_((VersionStatus.READY, VersionStatus.IN_PROGRESS)))
            .order_by(ProjectTodo.created_at, ProjectTodo.id)
            .limit(celery_settings.planned_todo_batch_size)
        )
        rows = result.all()
        run_ids: list[str] = []
        for project_id, todo_id in rows:
            try:
                run = await service.enqueue_planned_todo(
                    CreateAgentRunRequest(
                        project_id=project_id,
                        todo_id=todo_id,
                        push=True,
                    )
                )
            except AgentRunConflictError:
                logger.info("Todo %s was claimed by another dispatcher", todo_id)
                continue
            branch_task = await service.session.scalar(
                select(GithubWorkflowTask).where(
                    GithubWorkflowTask.action == GithubTaskAction.CREATE_TODO_BRANCH,
                    GithubWorkflowTask.todo_id == todo_id,
                )
            )
            if branch_task is None or branch_task.status == GithubTaskStatus.SUCCEEDED:
                run_ids.append(run.id)
        return run_ids


async def execute_run(run_id: str) -> dict[str, Any]:
    async with agent_service() as service:
        run = await service.execute_queued_run(run_id)
        return AgentRunResponse.model_validate(run).model_dump(mode="json", by_alias=True)


async def release_unpublished_run(run_id: str, error: str) -> None:
    async with agent_service() as service:
        await service.release_queued_run(run_id, error)


async def fail_active_run(run_id: str, error: str) -> dict[str, Any]:
    async with agent_service() as service:
        run = await service.fail_active_run(run_id, error)
        return AgentRunResponse.model_validate(run).model_dump(mode="json", by_alias=True)


def publish_completion_event(run_data: dict[str, Any]) -> None:
    run = AgentRunResponse.model_validate(run_data)
    event = AgentRunCompletedEvent.from_run(run)
    try:
        get_agent_event_broker().publish(event)
    except RedisError:
        logger.warning(
            "Unable to publish completion event for agent run %s",
            run.id,
            exc_info=True,
        )


@celery_app.task(name="agents.dispatch_planned_todos")
def dispatch_planned_todos() -> dict[str, int]:
    run_ids = asyncio.run(claim_planned_todos())
    published = 0
    for run_id in run_ids:
        try:
            execute_agent_run.apply_async(args=[run_id])
        except Exception as exc:
            logger.exception("Unable to publish queued agent run %s", run_id)
            asyncio.run(
                release_unpublished_run(
                    run_id,
                    f"Unable to publish Celery task: {exc}",
                )
            )
        else:
            published += 1
    return {"claimed": len(run_ids), "published": published}


@celery_app.task(
    bind=True,
    name="agents.execute_agent_run",
    max_retries=None,
)
def execute_agent_run(task: Any, run_id: str) -> dict[str, Any]:
    celery_settings = get_celery_settings()
    try:
        with agent_execution_lock() as acquired:
            if not acquired:
                logger.info(
                    "Another agent run is active; retrying queued run %s",
                    run_id,
                )
                raise task.retry(countdown=celery_settings.agent_execution_lock_retry_seconds)

            try:
                result = asyncio.run(execute_run(run_id))
            except Exception as exc:
                logger.exception(
                    "Unexpected failure while executing agent run %s",
                    run_id,
                )
                failed_result = asyncio.run(
                    fail_active_run(run_id, f"Unexpected worker failure: {exc}")
                )
                publish_completion_event(failed_result)
                raise
            if result["status"] == AgentRunStatus.FAILED:
                publish_completion_event(result)
            return result
    except RedisError as exc:
        logger.warning(
            "Redis unavailable while acquiring the agent execution lock for %s",
            run_id,
            exc_info=True,
        )
        raise task.retry(
            exc=exc,
            countdown=celery_settings.agent_execution_lock_retry_seconds,
        ) from exc
