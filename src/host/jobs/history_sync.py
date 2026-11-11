import asyncio
import logging
from collections import Counter
from collections.abc import Callable, Mapping
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any

from application import SyncConfigurationService
from application.ports import RateHistoryProvider
from core.configuration.history_sync_config import HistorySyncSettings
from core.database.errors import ConcurrencyError
from core.database.session import Database
from core.jobs.base import PeriodicJob
from core.jobs.locking import try_advisory_xact_lock
from domain.models import SyncConfig
from infrastructure.db.repositories.rate_repository import SqlRateRepository
from infrastructure.db.repositories.sync_configuration_repository import (
    SqlSyncConfigurationRepository,
)

logger = logging.getLogger(__name__)

type HistoryProviderFactory = Callable[[str, Mapping[str, Any] | None], RateHistoryProvider]


class Outcome(StrEnum):
    SYNCED = "synced"
    REFRESHED = "refreshed"
    SKIPPED = "skipped"
    FAILED = "failed"


class SyncConfigurationJob(PeriodicJob):

    def __init__(self, db: Database, providers: HistoryProviderFactory,
                 settings: HistorySyncSettings) -> None:
        super().__init__(settings.interval_seconds)
        self._db = db
        self._providers = providers
        self._settings = settings
        self._slots = asyncio.Semaphore(settings.max_concurrency)
        self._provider_slots: dict[str, asyncio.Semaphore] = {}

    async def run_once(self) -> None:
        today = datetime.now(UTC).date()
        async with self._db.session() as session:
            configs = await SqlSyncConfigurationRepository(session).list_due(today)
        if not configs:
            return

        outcomes: Counter[Outcome] = Counter()
        async with asyncio.TaskGroup() as tg:
            for config in configs:
                tg.create_task(self._run_limited(config, today, outcomes))
        level = logging.DEBUG if outcomes.keys() <= {Outcome.REFRESHED} else logging.INFO
        logger.log(level, "%s: %d due, %d synced, %d refreshed, %d skipped, %d failed",
                   self.name, len(configs), outcomes[Outcome.SYNCED], outcomes[Outcome.REFRESHED],
                   outcomes[Outcome.SKIPPED], outcomes[Outcome.FAILED])

    async def _run_limited(self, config: SyncConfig, today: date,
                           outcomes: Counter[Outcome]) -> None:
        provider_slots = self._provider_slots.setdefault(
            config.provider, asyncio.Semaphore(self._settings.per_provider_concurrency))
        async with self._slots, provider_slots:
            outcomes[await self._sync(config, today)] += 1

    async def _sync(self, config: SyncConfig, today: date) -> Outcome:
        label = f"{config.provider} {config.base}/{config.quote} {config.interval}"
        try:
            async with asyncio.timeout(self._settings.config_timeout_seconds):
                async with self._db.transaction() as session:
                    if not await try_advisory_xact_lock(session, f"sync-config:{config.id}"):
                        return Outcome.SKIPPED
                    service = SyncConfigurationService(
                        self._providers(config.provider, config.options),
                        SqlSyncConfigurationRepository(session), SqlRateRepository(session))
                    result = await service.run(config, today)
        except ConcurrencyError:
            logger.debug("%s: %s was advanced by another worker", self.name, label)
            return Outcome.SKIPPED
        except Exception as e:
            error = f"{type(e).__name__}: {e}" if str(e) else type(e).__name__
            logger.warning("%s: %s failed: %s", self.name, label, error)
            await self._record_failure(config, error)
            return Outcome.FAILED

        if result.provisional:
            logger.debug("%s: %s %s (provisional) fetched %d, changed %d", self.name, label,
                         result.start, result.fetched, result.stored)
            return Outcome.REFRESHED
        logger.info("%s: %s %s..%s fetched %d, stored %d", self.name, label,
                    result.start, result.end, result.fetched, result.stored)
        return Outcome.SYNCED

    async def _record_failure(self, config: SyncConfig, error: str) -> None:
        try:
            async with self._db.transaction() as session:
                await SqlSyncConfigurationRepository(session).record_failure(config.id, error)
        except Exception:
            logger.exception("%s: could not record failure for %s", self.name, config.id)
