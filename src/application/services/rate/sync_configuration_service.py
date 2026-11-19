from datetime import date

from application.ports import RateHistoryProvider, RateRepository, SyncConfigurationRepository
from application.services.rate.models import ConfigSyncResult
from domain.models import SyncConfig, Rate


class SyncConfigurationService:

    def __init__(self, provider: RateHistoryProvider, configs: SyncConfigurationRepository,
                 rates: RateRepository) -> None:
        self._provider = provider
        self._configs = configs
        self._rates = rates

    async def _refresh(self, config: SyncConfig, today: date) -> ConfigSyncResult:
        if config.date_to is not None and config.date_to < today:
            return ConfigSyncResult(config.id, today, today, fetched=0, stored=0,
                                    provisional=True)
        rates = await self._provider.get_history(config.base, config.quote, today, today,
                                                 config.interval)
        stored = await self._rates.upsert_many(rates) if rates else 0
        return ConfigSyncResult(config.id, today, today, fetched=len(rates), stored=stored,
                                provisional=True)

    async def upsert_rates(self, rates: list[Rate], config):
        await self._rates.upsert_many(rates) if rates else 0

    async def advance(self, config: SyncConfig, end: date):
        await self._configs.advance(config, end)
