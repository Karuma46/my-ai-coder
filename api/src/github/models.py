from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.projects.models import utc_now


class GithubWorkflowTask(Base):
    __tablename__ = "github_workflow_task"
    __table_args__ = (
        UniqueConstraint(
            "action",
            "version_id",
            "todo_id",
            name="github_workflow_task_target_key",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("project.id", ondelete="CASCADE"),
        index=True,
    )
    version_id: Mapped[str | None] = mapped_column(
        ForeignKey("project_version.id", ondelete="CASCADE"),
        index=True,
    )
    todo_id: Mapped[str | None] = mapped_column(
        ForeignKey("project_todo.id", ondelete="CASCADE"),
        index=True,
    )
    action: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(20), index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
