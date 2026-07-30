from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.accounts import models as account_models  # noqa: F401
from src.accounts.handlers import register_account_exception_handlers
from src.accounts.router import router as account_router
from src.agents import models as agent_models  # noqa: F401
from src.agents.handlers import register_agent_exception_handlers
from src.agents.router import router as agent_router
from src.config import settings
from src.database import DatabaseSession, create_tables
from src.github import models as github_workflow_models  # noqa: F401
from src.github.config import get_github_settings
from src.github.handlers import register_github_exception_handlers
from src.github.mcp import mcp
from src.github.router import router as github_router
from src.items import models as item_models  # noqa: F401
from src.items.router import router as items_router
from src.projects import models as project_models  # noqa: F401
from src.projects.handlers import register_project_exception_handlers
from src.projects.router import router as projects_router

mcp_app = mcp.http_app(path="/mcp")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await create_tables()
    async with mcp_app.lifespan(app):
        yield


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
    routes=[*mcp_app.routes],
)
app.include_router(items_router)
app.include_router(github_router)
app.include_router(account_router)
app.include_router(projects_router)
app.include_router(agent_router)
register_github_exception_handlers(app)
register_account_exception_handlers(app)
register_project_exception_handlers(app)
register_agent_exception_handlers(app)


@app.get(
    "/health",
    tags=["System"],
    summary="Get API and dependency health",
    response_model=None,
)
async def health_check(session: DatabaseSession) -> Any:
    try:
        await session.execute(text("SELECT 1"))
        database_status = "operational"
    except SQLAlchemyError:
        database_status = "unavailable"

    github = get_github_settings()
    github_status = (
        "operational"
        if github.enabled
        and github.owner
        and github.personal_access_token is not None
        and bool(github.personal_access_token.get_secret_value())
        else "unavailable"
    )
    overall_status = (
        "operational"
        if database_status == "operational" and github_status == "operational"
        else "degraded"
    )
    payload = {
        "status": overall_status,
        "checkedAt": datetime.now(UTC).isoformat(),
        "services": [
            {"name": "database", "status": database_status},
            {"name": "github", "status": github_status},
        ],
    }
    if database_status == "unavailable":
        payload["status"] = "unavailable"
        return JSONResponse(status_code=503, content=payload)
    return payload
