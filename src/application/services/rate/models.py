from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import UUID

from domain import IntervalKind, SyncConfig, SyncProgress


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
