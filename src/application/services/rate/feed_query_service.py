from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from application.ports import ProviderCatalog, RateRepository, SyncConfigurationRepository
from core.clock import utc_today
from domain.enums import IntervalKind
from domain.models import ProviderPair, Rate


@dataclass(frozen=True, slots=True)
class FeedView:
    pair: ProviderPair
    latest: Rate | None
    previous: Rate | None

    @property
    def change_percent(self) -> Decimal | None:
        if self.latest is None or self.previous is None or self.previous.value == 0:
            return None
        return (self.latest.value - self.previous.value) / self.previous.value * 100


class FeedQueryService:
    def __init__(self, configs: SyncConfigurationRepository, rates: RateRepository,
                 catalog: ProviderCatalog, today: Callable[[], date] = utc_today) -> None:
        self._configs = configs
        self._rates = rates
        self._catalog = catalog
        self._today = today

    async def all(self) -> list[FeedView]:
        pairs = {(p.provider_id, p.base, p.quote): p for p in await self._catalog.pairs()}
        collected = [pairs[key] for c in await self._configs.list_active(IntervalKind.DAILY)
                     if (key := (c.provider_id, c.base, c.quote)) in pairs]
        return [await self._view(p) for p in collected]

    async def get(self, pair_id: UUID) -> FeedView | None:
        pair = await self._catalog.get_pair_by_id(pair_id)
        return await self._view(pair) if pair is not None else None

    async def history(self, pair_id: UUID, days: int) -> list[Rate] | None:
        pair = await self._catalog.get_pair_by_id(pair_id)
        if pair is None:
            return None
        since = datetime.combine(self._today() - timedelta(days=days), datetime.min.time(),
                                 tzinfo=UTC)
        return await self._rates.provider_series(pair.base, pair.quote, pair.provider,
                                                 since=since)

    async def last_completed_day(self, pair: ProviderPair) -> tuple[Rate, Rate | None] | None:
        today = self._today()
        recent = await self._rates.provider_series(pair.base, pair.quote, pair.provider,
                                                   limit=4, newest_first=True)
        final = [r for r in recent if r.as_of.date() < today]
        if not final:
            return None
        return final[0], final[1] if len(final) > 1 else None

    async def _view(self, pair: ProviderPair) -> FeedView:
        recent = await self._rates.provider_series(pair.base, pair.quote, pair.provider,
                                                   limit=2, newest_first=True)
        return FeedView(pair, recent[0] if recent else None,
                        recent[1] if len(recent) > 1 else None)
