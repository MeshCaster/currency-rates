from typing import Annotated, AsyncIterator, Callable, Coroutine, Any

from fastapi import Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from core.configuration.settings import Settings

import httpx

from core.database.session import Database
from core.exceptions.forbidden_error import ForbiddenError
from core.exceptions.unauthorized_error import UnauthorizedError
from core.exceptions.unavailable_service_error import ServiceUnavailableError
from core.security.token import TokenPayload, decode_access_token


def get_app_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


SettingsDep = Annotated[Settings, Depends(get_app_settings)]


def get_http_client(request: Request) -> httpx.AsyncClient:
    client: httpx.AsyncClient = request.state.http_client
    return client

HttpClientDep = Annotated[httpx.AsyncClient, Depends(get_http_client)]

def get_database(request: Request) -> Database:
    db: Database | None = getattr(request.state, "db", None)
    if db is None:
        raise ServiceUnavailableError("Database is not configured")
    return db


DatabaseDep = Annotated[Database, Depends(get_database)]


async def get_db_session(db: DatabaseDep) -> AsyncIterator[AsyncSession]:
    async with db.transaction() as session:
        yield session


DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]

_bearer = HTTPBearer(auto_error=False, description="JWT access token")

async def get_current_principal(
    settings: SettingsDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> TokenPayload:
    if credentials is None:
        raise UnauthorizedError("Missing bearer token", code="missing_token")
    return decode_access_token(credentials.credentials, settings.security)


CurrentPrincipalDep = Annotated[TokenPayload, Depends(get_current_principal)]

def require_scopes(
    *required: str,
) -> Callable[[TokenPayload], Coroutine[Any, Any, TokenPayload]]:

    async def checker(principal: CurrentPrincipalDep) -> TokenPayload:
        missing = sorted(set(required) - set(principal.scopes))
        if missing:
            raise ForbiddenError(
                f"Missing required scope(s): {', '.join(missing)}", code="insufficient_scope"
            )
        return principal

    return checker

class PaginationParams(BaseModel):
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)

PaginationDep = Annotated[PaginationParams, Query()]