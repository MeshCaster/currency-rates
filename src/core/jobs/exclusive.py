import logging
from abc import abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession

from core.database.session import Database
from core.jobs.base import PeriodicJob
from core.jobs.locking import try_advisory_xact_lock

logger = logging.getLogger(__name__)


class ExclusiveJob(PeriodicJob):

    def __init__(self, db: Database, interval_seconds: float,
                 timeout_seconds: float | None = None) -> None:
        super().__init__(interval_seconds, timeout_seconds)
        self._db = db

    async def run_once(self) -> None:
        async with self._db.transaction() as session:
            if not await try_advisory_xact_lock(session, self.name):
                logger.debug("%s: another replica holds the lock, skipping this tick", self.name)
                return
            await self.run_exclusive(session)

    @abstractmethod
    async def run_exclusive(self, session: AsyncSession) -> None:
        pass
