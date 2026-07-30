import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.agents.celery_app import celery_app
from src.agents.models import AgentRun
from src.config import settings as app_settings
from src.github.config import get_github_settings
from src.github.models import GithubWorkflowTask
from src.github.service import GithubService
from src.github.workflow import GithubTaskStatus, GithubWorkflowExecutor


@asynccontextmanager
async def workflow_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(app_settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            yield session
    finally:
        await engine.dispose()


async def claim_next_github_task() -> str | None:
    async with workflow_session() as session:
        running = await session.scalar(
            select(GithubWorkflowTask.id)
            .where(GithubWorkflowTask.status == GithubTaskStatus.RUNNING)
            .limit(1)
        )
        if running is not None:
            return None
        pending_id = await session.scalar(
            select(GithubWorkflowTask.id)
            .where(GithubWorkflowTask.status == GithubTaskStatus.PENDING)
            .order_by(GithubWorkflowTask.created_at, GithubWorkflowTask.id)
            .limit(1)
        )
        if pending_id is None:
            return None
        claimed = await session.scalar(
            update(GithubWorkflowTask)
            .where(
                GithubWorkflowTask.id == pending_id,
                GithubWorkflowTask.status == GithubTaskStatus.PENDING,
            )
            .values(status=GithubTaskStatus.RUNNING)
            .returning(GithubWorkflowTask.id)
        )
        await session.commit()
        return claimed


async def release_github_task(task_id: str, error: str) -> None:
    async with workflow_session() as session:
        task = await session.get(GithubWorkflowTask, task_id)
        if task is not None and task.status == GithubTaskStatus.RUNNING:
            task.status = GithubTaskStatus.PENDING
            task.error = error
            await session.commit()


async def keep_github_task_active(task_id: str, error: str) -> None:
    async with workflow_session() as session:
        task = await session.get(GithubWorkflowTask, task_id)
        if task is not None:
            task.status = GithubTaskStatus.RUNNING
            task.error = error
            task.completed_at = None
            await session.commit()


async def run_github_workflow_task(task_id: str) -> tuple[list[str], str | None]:
    async with workflow_session() as session:
        executor = GithubWorkflowExecutor(
            session,
            GithubService(get_github_settings()),
        )
        _, run_ids, completed_run_id = await executor.execute(task_id)
        return run_ids, completed_run_id


@celery_app.task(name="github.dispatch-workflow-tasks")
def dispatch_github_workflow_tasks() -> dict[str, int]:
    task_id = asyncio.run(claim_next_github_task())
    if task_id is None:
        return {"dispatched": 0}
    try:
        execute_github_workflow_task.apply_async(args=[task_id])
    except Exception as exc:
        asyncio.run(release_github_task(task_id, f"Unable to publish Celery task: {exc}"))
        raise
    return {"dispatched": 1}


@celery_app.task(
    bind=True,
    name="github.execute-workflow-task",
    max_retries=5,
)
def execute_github_workflow_task(task, task_id: str) -> dict[str, object]:
    try:
        run_ids, completed_run_id = asyncio.run(
            execute_github_workflow_task_async(task_id)
        )
    except Exception as exc:
        if task.request.retries < task.max_retries:
            asyncio.run(keep_github_task_active(task_id, str(exc)))
            raise task.retry(exc=exc, countdown=1) from exc
        raise
    from src.agents.tasks import execute_agent_run, publish_completion_event

    for run_id in run_ids:
        execute_agent_run.apply_async(args=[run_id])
    if completed_run_id is not None:
        run_data = asyncio.run(completed_agent_run(completed_run_id))
        publish_completion_event(run_data)
    return {"taskId": task_id, "agentRunsDispatched": len(run_ids)}


async def execute_github_workflow_task_async(
    task_id: str,
) -> tuple[list[str], str | None]:
    return await run_github_workflow_task(task_id)


async def completed_agent_run(run_id: str) -> dict[str, object]:
    from src.agents.schemas import AgentRunResponse

    async with workflow_session() as session:
        run = await session.get(AgentRun, run_id)
        if run is None:
            raise RuntimeError(f"Agent run '{run_id}' was not found")
        return AgentRunResponse.model_validate(run).model_dump(
            mode="json", by_alias=True
        )
