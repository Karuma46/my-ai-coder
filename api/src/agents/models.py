from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.projects.models import utc_now


class LocalAgent(Base):
    __tablename__ = "local_agent"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    company_id: Mapped[str] = mapped_column(
        ForeignKey("company.id", ondelete="CASCADE"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120))
    provider: Mapped[str] = mapped_column(String(20))
    model_name: Mapped[str] = mapped_column(String(255), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    command: Mapped[str] = mapped_column(String(2_048))
    repository_root: Mapped[str] = mapped_column(String(2_048), default=".")
    git_command: Mapped[str] = mapped_column(String(2_048), default="git")
    git_remote: Mapped[str] = mapped_column(String(255), default="origin")
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=3_600)
    max_output_characters: Mapped[int] = mapped_column(Integer, default=100_000)
    push_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class AgentRun(Base):
    __tablename__ = "agent_run"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("project.id", ondelete="CASCADE"),
        index=True,
    )
    todo_id: Mapped[str] = mapped_column(
        ForeignKey("project_todo.id", ondelete="CASCADE"),
        index=True,
    )
    local_agent_id: Mapped[str | None] = mapped_column(
        ForeignKey("local_agent.id", ondelete="SET NULL"),
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))
    branch_name: Mapped[str] = mapped_column(String(255))
    repository_path: Mapped[str] = mapped_column(String(2_048))
    pushed: Mapped[bool] = mapped_column(Boolean, default=False)
    exit_code: Mapped[int | None] = mapped_column(Integer)
    output: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
