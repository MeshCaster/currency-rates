import asyncio
import logging
from datetime import timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from application import PriceAlertService
from core.clock import utc_now, utc_today
from core.configuration.alert_config import AlertSettings
from core.database.session import Database
from core.jobs.exclusive import ExclusiveJob
from domain.alerts import PriceSample
from domain.enums import IntervalKind
from domain.models import SyncConfig
from host.jobs.history_sync import HistoryProviderFactory
from infrastructure.db.repositories.alert_repository import (
    SqlAlertRepository,
    SqlAlertRuleRepository,
    SqlPriceSampleRepository,
)
from infrastructure.db.repositories.sync_configuration_repository import (
    SqlSyncConfigurationRepository,
)

logger = logging.getLogger(__name__)


class PriceAlertJob(ExclusiveJob):

    def __init__(self, db: Database, providers: HistoryProviderFactory,
                 settings: AlertSettings) -> None:
        super().__init__(db, settings.interval_seconds, settings.timeout_seconds)
        self._providers = providers
        self._settings = settings
        self._slots = asyncio.Semaphore(settings.max_concurrency)

    async def run_exclusive(self, session: AsyncSession) -> None:
        now = utc_now()
        tick = timedelta(seconds=self._settings.interval_seconds)
        samples = SqlPriceSampleRepository(session)
        pruned = await samples.prune(now - timedelta(days=self._settings.sample_retention_days))
        rules = await SqlAlertRuleRepository(session).list_active()
        if not rules:
            return
        configs = await SqlSyncConfigurationRepository(session).get_many(
            {r.sync_configuration_id for r in rules})
        prices = await asyncio.gather(*(self._price(c) for c in configs))
        await samples.add_many([PriceSample(c.id, now, value)
                                for c, value in zip(configs, prices, strict=True)
                                if value is not None])
        service = PriceAlertService(SqlAlertRepository(session), samples,
                                    stale_after=2 * tick, slack=2 * tick)
        result = await service.evaluate(rules, now)

        level = logging.INFO if result.opened or result.escalated or result.resolved \
            else logging.DEBUG
        logger.log(level, "%s: %d rules, %d evaluated, %d opened, %d escalated, %d resolved, "
                   "%d skipped, %d samples pruned", self.name, len(rules), result.evaluated,
                   result.opened, result.escalated, result.resolved, len(result.skipped), pruned)

    async def _price(self, config: SyncConfig) -> Decimal | None:
        today = utc_today()
        try:
            async with self._slots:
                provider = self._providers(config.provider, config.options)
                rates = await provider.get_history(config.base, config.quote, today, today,
                                                   IntervalKind.DAILY)
        except Exception as e:
            logger.warning("%s: no price for %s %s/%s: %s", self.name, config.provider,
                           config.base, config.quote, e)
            return None
        return rates[-1].value if rates else None
