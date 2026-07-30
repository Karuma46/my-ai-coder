from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.accounts.exceptions import (
    AccountConflictError,
    AccountDomainError,
    AccountForbiddenError,
    AccountNotFoundError,
    AuthenticationError,
)
from src.errors import error_response


def register_account_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AuthenticationError)
    async def unauthorized(request: Request, exc: AuthenticationError) -> JSONResponse:
        response = error_response(
            request,
            status_code=status.HTTP_401_UNAUTHORIZED,
            code=exc.code,
            message=str(exc),
        )
        response.headers["WWW-Authenticate"] = "Bearer"
        return response

    @app.exception_handler(AccountForbiddenError)
    async def forbidden(request: Request, exc: AccountForbiddenError) -> JSONResponse:
        return error_response(
            request,
            status_code=status.HTTP_403_FORBIDDEN,
            code=exc.code,
            message=str(exc),
        )

    @app.exception_handler(AccountNotFoundError)
    async def not_found(request: Request, exc: AccountNotFoundError) -> JSONResponse:
        return error_response(
            request,
            status_code=status.HTTP_404_NOT_FOUND,
            code=exc.code,
            message=str(exc),
        )

    @app.exception_handler(AccountConflictError)
    async def conflict(request: Request, exc: AccountConflictError) -> JSONResponse:
        return error_response(
            request,
            status_code=status.HTTP_409_CONFLICT,
            code=exc.code,
            message=str(exc),
        )

    @app.exception_handler(AccountDomainError)
    async def domain_error(request: Request, exc: AccountDomainError) -> JSONResponse:
        return error_response(
            request,
            status_code=status.HTTP_400_BAD_REQUEST,
            code=exc.code,
            message=str(exc),
        )
