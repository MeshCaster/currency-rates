import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.configuration.settings import Settings

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine
        self.session_factory = async_sessionmaker(
            engine, expire_on_commit=False, autoflush=False, class_=AsyncSession
        )

    @classmethod
    def from_settings(cls, settings: Settings) -> Database:
        cfg = settings.database
        if cfg.url is None:
            raise ValueError("DATABASE__URL is not configured")
        url = cfg.url.get_secret_value()
        kwargs: dict[str, Any] = {"pool_pre_ping": cfg.pool_pre_ping, "echo": cfg.echo}
        if not url.startswith("sqlite"):
            kwargs |= {
                "pool_size": cfg.pool_size,
                "max_overflow": cfg.max_overflow,
                "pool_timeout": cfg.pool_timeout,
                "pool_recycle": cfg.pool_recycle,
            }
        return cls(create_async_engine(url, **kwargs))

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self.session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[AsyncSession]:
        async with self.session_factory.begin() as session:
            yield session

    async def ping(self) -> bool:
        try:
            async with self.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception as exc:
            logger.warning("Database ping failed: %s", exc.__class__.__name__)
            return False
        return True

    async def dispose(self) -> None:
        await self.engine.dispose()
