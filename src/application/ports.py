from datetime import date
from typing import Protocol, Sequence

from common.models import Page
from domain.models import Rate


class RateProvider(Protocol):

    name: str

    async def get_rate(self, base: str, quote: str) -> Rate: ...


class HistoricalRateProvider(Protocol):
    name: str

    async def get_rate(self, base: str, quote: str, on: date) -> Rate: ...


class RateRepository(Protocol):
    async def add_many(self, rates: Sequence[Rate]) -> int: ...
    async def latest(self, base: str, quote: str, source: str | None = None) -> Rate | None: ...
    async def history(self, base: str, quote: str, page: int = 1, size: int = 50,
                      official_only: bool = True) -> Page[Rate]: ...
    async def list_pairs(self, include_cross: bool = False) -> list[tuple[str, str]]: ...
