from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from domain.enums import CurrencyKind, IntervalKind, ProviderKind


@dataclass(frozen=True, slots=True)
class CurrencySeed:
    code: str
    name: str
    kind: CurrencyKind


@dataclass(frozen=True, slots=True)
class IntervalSeed:
    interval: IntervalKind
    is_native: bool
    history_start: date | None = None
    history_window_days: int | None = None
    max_points_per_request: int | None = None


@dataclass(frozen=True, slots=True)
class SyncSeed:
    base: str
    quote: str
    interval: IntervalKind
    days_back: int
    options: Mapping[str, Any] | None = None
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class ProviderSeed:
    key: str
    display_name: str
    kind: ProviderKind
    requires_api_key: bool = False
    intervals: tuple[IntervalSeed, ...] = ()
    currencies: tuple[str, ...] = ()
    provider_codes: Mapping[str, str] = field(default_factory=dict)
    dev_sync: tuple[SyncSeed, ...] = ()
