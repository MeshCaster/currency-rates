from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from application import SyncConfigurationView
from domain.enums import IntervalKind, SyncState, SyncStatus


class RateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    base: str
    quote: str
    value: Decimal
    source: str
    as_of: datetime


class RateHistoryOut(BaseModel):
    items: list[RateOut]
    total: int
    page: int
    size: int


class SyncFailureOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    base: str
    quote: str
    error: str


class SyncResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    fetched: int
    stored: int
    failures: list[SyncFailureOut]


class SyncProgressOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    state: SyncState
    percent: float = Field(description="Completed days synced, 0-100. Today is never counted.")
    days_synced: int
    days_total: int
    days_remaining: int


class SyncConfigurationOut(BaseModel):
    id: UUID
    provider: str
    base: str
    quote: str
    interval: IntervalKind
    date_from: date
    date_to: date | None
    synced_until: date | None
    is_active: bool
    options: dict[str, Any] | None
    last_run_at: datetime | None
    last_status: SyncStatus | None
    last_error: str | None
    progress: SyncProgressOut

    @classmethod
    def of(cls, view: SyncConfigurationView) -> SyncConfigurationOut:
        c = view.config
        return cls(id=c.id, provider=c.provider, base=c.base, quote=c.quote,
                   interval=c.interval, date_from=c.date_from, date_to=c.date_to,
                   synced_until=c.synced_until, is_active=c.is_active, options=c.options,
                   last_run_at=c.last_run_at, last_status=c.last_status,
                   last_error=c.last_error,
                   progress=SyncProgressOut.model_validate(view.progress))


class SyncConfigurationPageOut(BaseModel):
    items: list[SyncConfigurationOut]
    total: int
    page: int
    size: int
