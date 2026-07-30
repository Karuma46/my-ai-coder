from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class Project(Base):
    __tablename__ = "project"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    company_id: Mapped[str] = mapped_column(
        ForeignKey("company.id", ondelete="RESTRICT"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120))
    path: Mapped[str] = mapped_column(String(2_048))
    repository_slug: Mapped[str] = mapped_column(String(100), unique=True)
    default_branch: Mapped[str] = mapped_column(String(255), default="main")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    company: Mapped["Company"] = relationship(back_populates="projects")  # noqa: F821
    versions: Mapped[list["ProjectVersion"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by=lambda: ProjectVersion.created_at.desc(),
        lazy="selectin",
    )
    todos: Mapped[list["ProjectTodo"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by=lambda: ProjectTodo.created_at.desc(),
        lazy="selectin",
    )

    @property
    def wip_todos(self) -> list["ProjectTodo"]:
        return [todo for todo in self.todos if todo.version_id is None]


class ProjectVersion(Base):
    __tablename__ = "project_version"
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="project_version_project_id_name_key"),
        UniqueConstraint(
            "project_id",
            "branch_name",
            name="project_version_project_id_branch_name_key",
        ),
    )

    id: Mapped[str] = mapped_column(String(180), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("project.id", ondelete="CASCADE"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(60))
    summary: Mapped[str] = mapped_column(String(1_000))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    branch_name: Mapped[str] = mapped_column(String(255))
    pull_request_number: Mapped[int | None] = mapped_column(Integer)
    pull_request_url: Mapped[str | None] = mapped_column(String(2_048))
    merge_commit_sha: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    project: Mapped[Project] = relationship(back_populates="versions")
    todos: Mapped[list["ProjectTodo"]] = relationship(
        back_populates="version",
        order_by=lambda: ProjectTodo.created_at.desc(),
        lazy="selectin",
        passive_deletes=True,
    )


class ProjectTodo(Base):
    __tablename__ = "project_todo"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "issue_number",
            name="project_todo_project_id_issue_number_key",
        ),
        UniqueConstraint(
            "project_id",
            "branch_name",
            name="project_todo_project_id_branch_name_key",
        ),
    )

    id: Mapped[str] = mapped_column(String(220), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("project.id", ondelete="CASCADE"),
        index=True,
    )
    version_id: Mapped[str | None] = mapped_column(
        ForeignKey("project_version.id", ondelete="CASCADE"),
        index=True,
    )
    issue_number: Mapped[int] = mapped_column(Integer)
    issue_url: Mapped[str | None] = mapped_column(String(2_048))
    title: Mapped[str] = mapped_column(String(256))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(20),
        default="draft",
        server_default="draft",
    )
    branch_name: Mapped[str | None] = mapped_column(String(255))
    pull_request_number: Mapped[int | None] = mapped_column(Integer)
    pull_request_url: Mapped[str | None] = mapped_column(String(2_048))
    is_merged: Mapped[bool] = mapped_column(Boolean, default=False)
    merge_commit_sha: Mapped[str | None] = mapped_column(String(64))
    merged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    project: Mapped[Project] = relationship(back_populates="todos")
    version: Mapped[ProjectVersion | None] = relationship(back_populates="todos")
