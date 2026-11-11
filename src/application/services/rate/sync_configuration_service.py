from datetime import date, timedelta

from application.ports import RateHistoryProvider, RateRepository, SyncConfigurationRepository
from application.services.rate.models import ConfigSyncResult
from domain.enums import IntervalKind
from domain.errors import UnsupportedSyncError
from domain.models import SyncConfig


class SyncConfigurationService:

    def __init__(self, provider: RateHistoryProvider, configs: SyncConfigurationRepository,
                 rates: RateRepository) -> None:
        self._provider = provider
        self._configs = configs
        self._rates = rates

    async def run(self, config: SyncConfig, today: date) -> ConfigSyncResult:
        if config.interval is not IntervalKind.DAILY:
            raise UnsupportedSyncError(f"{config.interval} sync is not supported yet")

        start = config.next_date
        if start >= today:
            return await self._refresh(config, today)

        end = min(start + timedelta(days=self._provider.chunk_days - 1),
                  today - timedelta(days=1))
        if config.date_to is not None:
            end = min(end, config.date_to)
        if start > end:
            return ConfigSyncResult(config.id, start, end, fetched=0, stored=0)

        rates = await self._provider.get_history(config.base, config.quote, start, end,
                                                 config.interval)
        stored = await self._rates.upsert_many(rates) if rates else 0
        await self._configs.advance(config, end)
        return ConfigSyncResult(config.id, start, end, fetched=len(rates), stored=stored)

    async def _refresh(self, config: SyncConfig, today: date) -> ConfigSyncResult:
        if config.date_to is not None and config.date_to < today:
            return ConfigSyncResult(config.id, today, today, fetched=0, stored=0,
                                    provisional=True)
        rates = await self._provider.get_history(config.base, config.quote, today, today,
                                                 config.interval)
        stored = await self._rates.upsert_many(rates) if rates else 0
        return ConfigSyncResult(config.id, today, today, fetched=len(rates), stored=stored,
                                provisional=True)
