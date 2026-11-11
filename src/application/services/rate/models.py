from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import UUID

from domain import IntervalKind, Rate, SyncConfig, SyncProgress


@dataclass(frozen=True, slots=True)
class SyncFailure:
    base: str
    quote: str
    error: str


@dataclass(frozen=True, slots=True)
class SyncResult:
    rates: list[Rate]
    stored: int
    failures: list[SyncFailure]

    @property
    def fetched(self) -> int:
        return len(self.rates)

    @property
    def ok(self) -> bool:
        return not self.failures

@dataclass(frozen=True, slots=True)
class ConfigSyncResult:
    config_id: UUID
    start: date
    end: date
    fetched: int
    stored: int
    provisional: bool = False


@dataclass(frozen=True, slots=True)
class SyncConfigurationView:
    config: SyncConfig
    progress: SyncProgress


@dataclass(frozen=True, slots=True)
class NewSyncConfiguration:
    provider: str
    base: str
    quote: str
    interval: IntervalKind
    date_from: date
    date_to: date | None = None
    options: Mapping[str, Any] | None = None
    is_active: bool = True
