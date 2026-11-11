from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from typing import TYPE_CHECKING, TypedDict

import httpx

from core.database.session import Database

if TYPE_CHECKING:
    from fastapi import FastAPI

    from core.configuration.settings import Settings

logger = logging.getLogger(__name__)


class AppState(TypedDict):
    http_client: httpx.AsyncClient
    db: Database | None


def create_http_client(settings: Settings) -> httpx.AsyncClient:
    cfg = settings.http_client
    return httpx.AsyncClient(
        timeout=httpx.Timeout(cfg.timeout),
        limits=httpx.Limits(
            max_connections=cfg.max_connections,
            max_keepalive_connections=cfg.max_keepalive_connections,
        ),
        transport=httpx.AsyncHTTPTransport(retries=cfg.connect_retries),
        headers={"User-Agent": f"{settings.app_name}/{settings.app_version}"},
        follow_redirects=False,
    )


@asynccontextmanager
async def app_resources(settings: Settings) -> AsyncIterator[AppState]:
    async with AsyncExitStack() as stack:
        http_client = await stack.enter_async_context(create_http_client(settings))

        db: Database | None = None
        if settings.database.enabled:
            db = Database.from_settings(settings)
            stack.push_async_callback(db.dispose)
            if not await db.ping():
                logger.warning("Database not reachable at startup; readiness will report it")

        yield {"http_client": http_client, "db": db}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[AppState]:
    settings: Settings = app.state.settings
    logger.info(
        "Starting %s v%s",
        settings.app_name,
        settings.app_version,
        extra={"environment": settings.app_env.value},
    )

    async with app_resources(settings) as state:
        logger.info("Startup complete")
        yield state
        logger.info("Shutting down")
