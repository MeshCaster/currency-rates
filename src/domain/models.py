from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import List

from domain.enums import IntervalKind


@dataclass(frozen=True, slots=True)
class Rate:

    base: str
    quote: str
    value: Decimal
    source: str
    as_of: datetime

@dataclass(frozen=True, slots=True)
class SyncConfiguration:

    configurations: List[SyncConfiguration]

@dataclass(frozen=True, slots=True)
class TickerSyncConfig:
    ticker: str
    provider: str
    interval: IntervalKind
    date_from: datetime
    date_to: datetime
