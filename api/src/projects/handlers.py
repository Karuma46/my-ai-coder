from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.errors import error_response
from src.projects.exceptions import (
    ProjectConflictError,
    ProjectDomainError,
    ProjectGithubReferenceError,
    ProjectNotFoundError,
)


def register_project_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ProjectNotFoundError)
    async def not_found(request: Request, exc: ProjectNotFoundError) -> JSONResponse:
        return error_response(
            request,
            status_code=status.HTTP_404_NOT_FOUND,
            code=exc.code,
            message=str(exc),
        )

    @app.exception_handler(ProjectConflictError)
    async def conflict(request: Request, exc: ProjectConflictError) -> JSONResponse:
        return error_response(
            request,
            status_code=status.HTTP_409_CONFLICT,
            code=exc.code,
            message=str(exc),
        )

    @app.exception_handler(ProjectGithubReferenceError)
    async def github_reference(
        request: Request,
        exc: ProjectGithubReferenceError,
    ) -> JSONResponse:
        return error_response(
            request,
            status_code=status.HTTP_502_BAD_GATEWAY,
            code=exc.code,
            message=str(exc),
        )

    @app.exception_handler(ProjectDomainError)
    async def domain_error(request: Request, exc: ProjectDomainError) -> JSONResponse:
        return error_response(
            request,
            status_code=status.HTTP_400_BAD_REQUEST,
            code=exc.code,
            message=str(exc),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {
                "field": ".".join(str(part) for part in error["loc"] if part != "body"),
                "message": error["msg"],
            }
            for error in exc.errors()
        ]
        return error_response(
            request,
            status_code=status.HTTP_400_BAD_REQUEST,
            code="VALIDATION_ERROR",
            message="The request contains invalid fields.",
            details=details,
        )
