from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from domain.enums import CurrencyKind, IntervalKind, ProviderKind
from domain.models import IntervalCapability


@dataclass(frozen=True, slots=True)
class CurrencySeed:
    code: str
    name: str
    kind: CurrencyKind

    @property
    def icon(self) -> str:
        return f"currency-icons/{self.code.lower()}.svg"


@dataclass(frozen=True, slots=True)
class PairSeed:
    base: str
    quote: str
    symbol: str | None = None


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
    intervals: tuple[IntervalCapability, ...] = ()
    pairs: tuple[PairSeed, ...] = ()
    dev_sync: tuple[SyncSeed, ...] = ()
