import logging
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from application.ports import RateProvider
from application import RateSyncService
from host.jobs.base import PeriodicJob
from infrastructure.db.repositories.rate_repository import SqlRateRepository

logger = logging.getLogger(__name__)


class RateSyncJob(PeriodicJob):
    def __init__(self, provider: RateProvider, session_factory: async_sessionmaker[AsyncSession],
                 pairs: Sequence[tuple[str, str]], interval_seconds: float = 10.0) -> None:
        super().__init__(interval_seconds)
        self._provider = provider
        self._session_factory = session_factory
        self._pairs = list(pairs)

    async def run_once(self) -> None:
        async with self._session_factory() as session:
            service = RateSyncService(self._provider, SqlRateRepository(session))
            result = await service.sync_many(self._pairs)
            await session.commit()
            logger.info("%s: fetched %d, stored %d, failed %d (provider=%s)", self.name,
                        result.fetched, result.stored, len(result.failures), self._provider.name)
            for f in result.failures:
                logger.warning("%s: %s/%s failed: %s", self.name, f.base, f.quote, f.error)
