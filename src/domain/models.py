from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from enums import IntervalKind, ProviderKind, SyncStatus

@dataclass(frozen=True, slots=True)
class Rate:

    base: str
    quote: str
    value: Decimal
    source: str
    as_of: datetime

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
