from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.accounts.config import AuthSettings, get_auth_settings
from src.accounts.exceptions import AuthenticationError
from src.accounts.models import User
from src.accounts.security import decode_access_token
from src.accounts.service import AccountService
from src.database import DatabaseSession

bearer_scheme = HTTPBearer(auto_error=False, scheme_name="bearerAuth")


async def get_account_service(
    session: DatabaseSession,
    settings: Annotated[AuthSettings, Depends(get_auth_settings)],
) -> AccountService:
    return AccountService(session, settings)


AccountServiceDep = Annotated[AccountService, Depends(get_account_service)]


async def get_current_user(
    session: DatabaseSession,
    settings: Annotated[AuthSettings, Depends(get_auth_settings)],
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("Authentication is required")
    user_id = decode_access_token(credentials.credentials, settings)
    user = await session.get(User, user_id)
    if user is None:
        raise AuthenticationError("The authenticated user no longer exists")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
