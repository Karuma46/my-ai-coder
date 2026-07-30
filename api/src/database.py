from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends
from sqlalchemy import event, inspect, text
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from src.config import settings


class Base(AsyncAttrs, DeclarativeBase):
    pass


engine = create_async_engine(settings.database_url)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)

if settings.database_url.startswith("sqlite"):

    @event.listens_for(engine.sync_engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        yield session


DatabaseSession = Annotated[AsyncSession, Depends(get_db)]


async def create_tables() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        if settings.database_url.startswith("sqlite"):
            local_agent_columns = await connection.run_sync(
                lambda sync_connection: {
                    column["name"]
                    for column in inspect(sync_connection).get_columns("local_agent")
                }
            )
            if "model_name" not in local_agent_columns:
                await connection.execute(
                    text(
                        "ALTER TABLE local_agent ADD COLUMN model_name "
                        "VARCHAR(255) NOT NULL DEFAULT ''"
                    )
                )
            if "is_default" not in local_agent_columns:
                await connection.execute(
                    text(
                        "ALTER TABLE local_agent ADD COLUMN is_default "
                        "BOOLEAN NOT NULL DEFAULT 0"
                    )
                )
            agent_run_columns = await connection.run_sync(
                lambda sync_connection: {
                    column["name"]
                    for column in inspect(sync_connection).get_columns("agent_run")
                }
            )
            if "local_agent_id" not in agent_run_columns:
                await connection.execute(
                    text("ALTER TABLE agent_run ADD COLUMN local_agent_id VARCHAR(36)")
                )
                await connection.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_agent_run_local_agent_id "
                        "ON agent_run (local_agent_id)"
                    )
                )
            columns = await connection.run_sync(
                lambda sync_connection: {
                    column["name"] for column in inspect(sync_connection).get_columns("project")
                }
            )
            if "company_id" not in columns:
                now = datetime.now(UTC)
                await connection.execute(
                    text(
                        "INSERT OR IGNORE INTO company "
                        "(id, name, created_at, updated_at) "
                        "VALUES ('legacy-workspace', 'Legacy Workspace', :now, :now)"
                    ),
                    {"now": now},
                )
                await connection.execute(
                    text("ALTER TABLE project ADD COLUMN company_id VARCHAR(120)")
                )
                await connection.execute(
                    text(
                        "UPDATE project SET company_id = 'legacy-workspace' "
                        "WHERE company_id IS NULL"
                    )
                )
                await connection.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS project_company_id_idx ON project (company_id)"
                    )
                )
            await connection.execute(
                text(
                    "CREATE TRIGGER IF NOT EXISTS project_company_required_insert "
                    "BEFORE INSERT ON project "
                    "WHEN NEW.company_id IS NULL "
                    "BEGIN SELECT RAISE(ABORT, 'project company_id is required'); END"
                )
            )
            await connection.execute(
                text(
                    "CREATE TRIGGER IF NOT EXISTS project_company_required_update "
                    "BEFORE UPDATE OF company_id ON project "
                    "WHEN NEW.company_id IS NULL "
                    "BEGIN SELECT RAISE(ABORT, 'project company_id is required'); END"
                )
            )
