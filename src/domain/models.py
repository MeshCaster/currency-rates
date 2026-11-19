from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from domain.enums import CurrencyKind, IntervalKind, ProviderKind, SyncState, SyncStatus


@dataclass(frozen=True, slots=True)
class Rate:

    base: str
    quote: str
    value: Decimal
    source: str
    as_of: datetime

@dataclass(frozen=True, slots=True)
class Currency:
    code: str
    name: str
    kind: CurrencyKind
    icon: str | None = None

@dataclass(frozen=True, slots=True)
class IntervalCapability:
    interval: IntervalKind
    is_native: bool
    history_start: date | None = None
    history_window_days: int | None = None
    max_points_per_request: int | None = None

    def earliest(self, today: date) -> date | None:
        candidates = [d for d in (
            self.history_start,
            today - timedelta(days=self.history_window_days) if self.history_window_days else None,
        ) if d is not None]
        return max(candidates) if candidates else None

@dataclass(frozen=True, slots=True)
class ProviderPair:
    id: UUID
    provider_id: UUID
    provider: str
    base: str
    quote: str
    symbol: str | None = None

    @property
    def label(self) -> str:
        return f"{self.base}/{self.quote}"


@dataclass(frozen=True, slots=True)
class ProviderCapability:
    id: UUID
    key: str
    display_name: str
    kind: ProviderKind
    requires_api_key: bool
    is_active: bool
    intervals: tuple[IntervalCapability, ...] = ()

    def interval(self, interval: IntervalKind) -> IntervalCapability | None:
        return next((c for c in self.intervals if c.interval is interval), None)

@dataclass(frozen=True, slots=True)
class SyncProgress:
    days_total: int
    days_synced: int
    state: SyncState

    @property
    def days_remaining(self) -> int:
        return self.days_total - self.days_synced

    @property
    def percent(self) -> float:
        if self.days_total == 0:
            return 0.0 if self.state is SyncState.PENDING else 100.0
        return round(100 * self.days_synced / self.days_total, 1)


@dataclass(slots=True)
class SyncConfig:

    id: UUID
    provider_id: UUID
    provider: str
    base: str
    quote: str
    interval: IntervalKind
    date_from: date
    date_to: date | None = None
    synced_until: date | None = None
    is_active: bool = True
    options: dict[str, Any] | None = None
    last_run_at: datetime | None = None
    last_status: SyncStatus | None = None
    last_error: str | None = None
    version: int = field(default=0, compare=False)

    @property
    def next_date(self) -> date:
        return self.synced_until + timedelta(days=1) if self.synced_until else self.date_from

    def is_finished(self) -> bool:
        return self.date_to is not None and self.synced_until is not None \
            and self.synced_until >= self.date_to

    def progress(self, today: date) -> SyncProgress:
        end = today - timedelta(days=1)
        if self.date_to is not None:
            end = min(end, self.date_to)
        total = max((end - self.date_from).days + 1, 0)
        synced = 0 if self.synced_until is None else \
            min(max((self.synced_until - self.date_from).days + 1, 0), total)
        return SyncProgress(total, synced, self._state(synced >= total))

    def _state(self, caught_up: bool) -> SyncState:
        if not self.is_active:
            return SyncState.PAUSED
        if self.last_status is SyncStatus.FAILED:
            return SyncState.FAILED
        if self.is_finished():
            return SyncState.COMPLETED
        if self.last_run_at is None:
            return SyncState.PENDING
        return SyncState.LIVE if caught_up else SyncState.BACKFILLING
