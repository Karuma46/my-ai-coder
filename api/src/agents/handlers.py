from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.agents.exceptions import (
    AgentConfigurationError,
    AgentRepositoryError,
    AgentRunConflictError,
    AgentRunNotFoundError,
)
from src.errors import error_response


def register_agent_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AgentConfigurationError)
    async def configuration_error(
        request: Request,
        exc: AgentConfigurationError,
    ) -> JSONResponse:
        return error_response(
            request,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code=exc.code,
            message=str(exc),
        )

    @app.exception_handler(AgentRunNotFoundError)
    async def not_found(request: Request, exc: AgentRunNotFoundError) -> JSONResponse:
        return error_response(
            request,
            status_code=status.HTTP_404_NOT_FOUND,
            code=exc.code,
            message=str(exc),
        )

    @app.exception_handler(AgentRunConflictError)
    async def conflict(request: Request, exc: AgentRunConflictError) -> JSONResponse:
        return error_response(
            request,
            status_code=status.HTTP_409_CONFLICT,
            code=exc.code,
            message=str(exc),
        )

    @app.exception_handler(AgentRepositoryError)
    async def repository_error(request: Request, exc: AgentRepositoryError) -> JSONResponse:
        return error_response(
            request,
            status_code=status.HTTP_409_CONFLICT,
            code=exc.code,
            message=str(exc),
        )
