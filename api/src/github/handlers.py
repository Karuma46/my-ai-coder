from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.errors import error_response
from src.github.exceptions import (
    GithubConfigurationError,
    GithubOperationDisabledError,
    GithubRepositoryNotAllowedError,
    GithubUpstreamError,
)


def register_github_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(GithubConfigurationError)
    async def configuration_error(
        request: Request,
        exc: GithubConfigurationError,
    ) -> JSONResponse:
        return error_response(
            request,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="GITHUB_NOT_CONFIGURED",
            message=str(exc),
        )

    @app.exception_handler(GithubRepositoryNotAllowedError)
    async def repository_not_allowed(
        request: Request,
        exc: GithubRepositoryNotAllowedError,
    ) -> JSONResponse:
        return error_response(
            request,
            status_code=status.HTTP_403_FORBIDDEN,
            code="GITHUB_REPOSITORY_NOT_ALLOWED",
            message=str(exc),
        )

    @app.exception_handler(GithubOperationDisabledError)
    async def operation_disabled(
        request: Request,
        exc: GithubOperationDisabledError,
    ) -> JSONResponse:
        return error_response(
            request,
            status_code=status.HTTP_403_FORBIDDEN,
            code="GITHUB_OPERATION_DISABLED",
            message=str(exc),
        )

    @app.exception_handler(GithubUpstreamError)
    async def upstream_error(request: Request, exc: GithubUpstreamError) -> JSONResponse:
        return error_response(
            request,
            status_code=status.HTTP_502_BAD_GATEWAY,
            code="GITHUB_UPSTREAM_ERROR",
            message=str(exc),
        )
