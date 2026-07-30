import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from functools import lru_cache
from typing import Literal

from redis import Redis
from redis.asyncio import Redis as AsyncRedis

from src.agents.celery_config import get_celery_settings
from src.agents.schemas import AgentRunResponse, AgentRunStatus
from src.projects.schemas import APIModel

logger = logging.getLogger(__name__)


class AgentRunCompletedEvent(APIModel):
    type: Literal["agent-run.completed"] = "agent-run.completed"
    run_id: str
    project_id: str
    todo_id: str
    status: AgentRunStatus
    completed_at: datetime
    error: str | None = None

    @classmethod
    def from_run(cls, run: AgentRunResponse) -> "AgentRunCompletedEvent":
        if run.status not in {AgentRunStatus.SUCCEEDED, AgentRunStatus.FAILED}:
            raise ValueError("Only completed agent runs can produce completion events")
        if run.completed_at is None:
            raise ValueError("A completed agent run must have a completion timestamp")
        return cls(
            run_id=run.id,
            project_id=run.project_id,
            todo_id=run.todo_id,
            status=run.status,
            completed_at=run.completed_at,
            error=run.error,
        )


class AgentEventBroker:
    def __init__(self, redis_url: str, channel: str) -> None:
        self.redis_url = redis_url
        self.channel = channel

    def publish(self, event: AgentRunCompletedEvent) -> None:
        client = Redis.from_url(self.redis_url)
        try:
            client.publish(
                self.channel,
                event.model_dump_json(by_alias=True),
            )
        finally:
            client.close()

    async def publish_async(self, event: AgentRunCompletedEvent) -> None:
        client = AsyncRedis.from_url(self.redis_url)
        try:
            await client.publish(
                self.channel,
                event.model_dump_json(by_alias=True),
            )
        finally:
            await client.aclose()

    @asynccontextmanager
    async def subscribe(self) -> AsyncIterator[AsyncIterator[AgentRunCompletedEvent]]:
        client = AsyncRedis.from_url(self.redis_url, decode_responses=True)
        pubsub = client.pubsub()
        await pubsub.subscribe(self.channel)
        try:
            yield self._events(pubsub)
        finally:
            await pubsub.unsubscribe(self.channel)
            await pubsub.aclose()
            await client.aclose()

    async def _events(self, pubsub) -> AsyncIterator[AgentRunCompletedEvent]:
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            data = message.get("data")
            if not isinstance(data, str):
                continue
            try:
                yield AgentRunCompletedEvent.model_validate(json.loads(data))
            except (ValueError, TypeError):
                logger.warning(
                    "Ignoring invalid agent completion event from Redis",
                    exc_info=True,
                )


@lru_cache
def get_agent_event_broker() -> AgentEventBroker:
    settings = get_celery_settings()
    return AgentEventBroker(
        redis_url=settings.broker_url,
        channel=settings.task_events_channel,
    )
