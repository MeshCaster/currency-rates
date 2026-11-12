from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from application.ports import RateRepository, SyncConfigurationRepository
from core.clock import utc_today
from domain.models import Rate, SyncConfig


@dataclass(frozen=True, slots=True)
class FeedView:
    config: SyncConfig
    latest: Rate | None
    previous: Rate | None

    @property
    def change_percent(self) -> Decimal | None:
        if self.latest is None or self.previous is None or self.previous.value == 0:
            return None
        return (self.latest.value - self.previous.value) / self.previous.value * 100


class FeedQueryService:
    def __init__(self, configs: SyncConfigurationRepository, rates: RateRepository,
                 today: Callable[[], date] = utc_today) -> None:
        self._configs = configs
        self._rates = rates
        self._today = today

    async def all(self) -> list[FeedView]:
        found = await self._configs.search(is_active=True, size=200)
        return [await self._view(c) for c in found.items]

    async def get(self, id: UUID) -> FeedView | None:
        config = await self._configs.get(id)
        return await self._view(config) if config is not None and config.is_active else None

    async def history(self, id: UUID, days: int) -> list[Rate] | None:
        config = await self._configs.get(id)
        if config is None or not config.is_active:
            return None
        since = datetime.combine(self._today() - timedelta(days=days), datetime.min.time(),
                                 tzinfo=UTC)
        return await self._rates.provider_series(config.base, config.quote, config.provider,
                                                 since=since)

    async def _view(self, config: SyncConfig) -> FeedView:
        recent = await self._rates.provider_series(config.base, config.quote, config.provider,
                                                   limit=2, newest_first=True)
        return FeedView(config, recent[0] if recent else None,
                        recent[1] if len(recent) > 1 else None)
