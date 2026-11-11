from datetime import date
from typing import Protocol, Sequence
from uuid import UUID

from core.pagination import Page
from domain.enums import IntervalKind
from domain.models import Rate, SyncConfig


class RateProvider(Protocol):

    name: str

    async def get_rate(self, base: str, quote: str) -> Rate: ...


class HistoricalRateProvider(Protocol):
    name: str

    async def get_rate(self, base: str, quote: str, on: date) -> Rate: ...


class RateHistoryProvider(Protocol):
    name: str
    chunk_days: int

    async def get_history(self, base: str, quote: str, start: date, end: date,
                          interval: IntervalKind) -> list[Rate]: ...


class RateRepository(Protocol):
    async def add_many(self, rates: Sequence[Rate]) -> int: ...
    async def upsert_many(self, rates: Sequence[Rate]) -> int: ...
    async def latest(self, base: str, quote: str, source: str | None = None) -> Rate | None: ...
    async def history(self, base: str, quote: str, page: int = 1, size: int = 50,
                      official_only: bool = True) -> Page[Rate]: ...
    async def list_pairs(self, include_cross: bool = False) -> list[tuple[str, str]]: ...


class SyncConfigurationRepository(Protocol):
    async def get(self, id: UUID) -> SyncConfig | None: ...
    async def search(self, *, provider: str | None = None, is_active: bool | None = None,
                     page: int = 1, size: int = 50) -> Page[SyncConfig]: ...
    async def list_due(self, as_of: date) -> list[SyncConfig]: ...
    async def advance(self, config: SyncConfig, synced_until: date) -> SyncConfig: ...
    async def record_failure(self, id: UUID, error: str) -> None: ...
