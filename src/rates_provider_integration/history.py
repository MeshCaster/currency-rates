from datetime import date, timedelta
from typing import Protocol

from domain.enums import IntervalKind
from domain.models import Rate
from rates_provider_integration.errors import RateProviderError


class DatedRateSource(Protocol):
    name: str

    async def get_rate(self, base: str, quote: str, on: date) -> Rate: ...


class DailyHistory:

    def __init__(self, source: DatedRateSource, chunk_days: int = 31) -> None:
        self._source = source
        self.name = source.name
        self.chunk_days = chunk_days

    async def get_history(self, base: str, quote: str, start: date, end: date,
                          interval: IntervalKind = IntervalKind.DAILY) -> list[Rate]:
        if interval is not IntervalKind.DAILY:
            raise RateProviderError(f"{self.name} serves daily rates only; got {interval}")
        rates: list[Rate] = []
        day = start
        while day <= end:
            rates.append(await self._source.get_rate(base, quote, day))
            day += timedelta(days=1)
        return rates
