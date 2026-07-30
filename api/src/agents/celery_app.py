from celery import Celery

from src.agents.celery_config import get_celery_settings
from src.agents.config import get_agent_settings

celery_settings = get_celery_settings()
agent_settings = get_agent_settings()

celery_app = Celery(
    "project-release-api",
    broker=celery_settings.broker_url,
    backend=celery_settings.result_backend,
    include=["src.agents.tasks", "src.github.tasks"],
)
celery_app.conf.update(
    beat_schedule={
        "dispatch-planned-todos": {
            "task": "agents.dispatch_planned_todos",
            "schedule": float(celery_settings.planned_todo_scan_seconds),
            "options": {
                "expires": float(celery_settings.planned_todo_scan_seconds),
            },
        },
        "dispatch-github-workflow-tasks": {
            "task": "github.dispatch-workflow-tasks",
            "schedule": float(celery_settings.github_task_scan_seconds),
            "options": {
                "expires": float(celery_settings.github_task_scan_seconds),
            },
        },
    },
    beat_schedule_filename="/tmp/project-release-celerybeat-schedule",
    broker_connection_retry_on_startup=True,
    enable_utc=True,
    result_expires=celery_settings.result_expires_seconds,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_time_limit=agent_settings.timeout_seconds + 600,
    worker_concurrency=1,
    worker_prefetch_multiplier=1,
    timezone="UTC",
)
