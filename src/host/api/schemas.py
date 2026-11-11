from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from application import AlertRuleChanges, NewAlertRule, NewSyncConfiguration, SyncConfigurationView
from domain.alerts import Alert, AlertRule, AlertTier
from domain.enums import (
    AlertSeverity,
    AlertStatus,
    IntervalKind,
    PriceDirection,
    SyncState,
    SyncStatus,
)


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


class SyncConfigurationIn(BaseModel):
    provider: str = Field(description="Provider key from the catalog, e.g. nbg")
    base: str = Field(min_length=3, max_length=10)
    quote: str = Field(min_length=3, max_length=10)
    interval: IntervalKind = IntervalKind.DAILY
    date_from: date
    date_to: date | None = Field(default=None, description="None = keep syncing new days")
    options: dict[str, Any] | None = Field(
        default=None, description='Provider-specific, e.g. {"providers": "ECB"} for frankfurter')
    is_active: bool = True

    @field_validator("base", "quote")
    @classmethod
    def _upper(cls, code: str) -> str:
        return code.strip().upper()

    def to_command(self) -> NewSyncConfiguration:
        return NewSyncConfiguration(
            provider=self.provider.strip().lower(), base=self.base, quote=self.quote,
            interval=self.interval, date_from=self.date_from, date_to=self.date_to,
            options=self.options, is_active=self.is_active)


class AlertTierModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    threshold_percent: Decimal = Field(gt=0, le=1000, description="Move size, e.g. 5 = 5%")
    severity: AlertSeverity

    def to_domain(self) -> AlertTier:
        return AlertTier(self.threshold_percent, self.severity)


class AlertRuleIn(BaseModel):
    sync_configuration_id: UUID = Field(description="Whose live price to watch")
    name: str = Field(min_length=1, max_length=120)
    window_minutes: int = Field(ge=1, description="Compare with the price this long ago")
    tiers: list[AlertTierModel] = Field(
        min_length=1, max_length=len(AlertSeverity),
        description="Higher threshold, higher severity, e.g. 3% warning and 5% critical")
    direction: PriceDirection = PriceDirection.BOTH
    is_active: bool = True

    def to_command(self) -> NewAlertRule:
        return NewAlertRule(self.sync_configuration_id, self.name, self.window_minutes,
                            [t.to_domain() for t in self.tiers], self.direction, self.is_active)


class AlertRulePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    window_minutes: int | None = Field(default=None, ge=1)
    tiers: list[AlertTierModel] | None = Field(default=None, min_length=1,
                                               max_length=len(AlertSeverity))
    direction: PriceDirection | None = None
    is_active: bool | None = None

    def to_changes(self) -> AlertRuleChanges:
        tiers = [t.to_domain() for t in self.tiers] if self.tiers is not None else None
        return AlertRuleChanges(self.name, self.window_minutes, tiers, self.direction,
                                self.is_active)


class AlertRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    sync_configuration_id: UUID
    provider: str
    base: str
    quote: str
    name: str
    window_minutes: int
    direction: PriceDirection
    tiers: list[AlertTierModel]
    is_active: bool

    @classmethod
    def of(cls, rule: AlertRule) -> AlertRuleOut:
        return cls.model_validate(rule)


class AlertRulePageOut(BaseModel):
    items: list[AlertRuleOut]
    total: int
    page: int
    size: int


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    rule_id: UUID
    severity: AlertSeverity
    status: AlertStatus
    opened_at: datetime
    change_percent: Decimal = Field(description="Latest move, signed: -5 = down 5%")
    peak_change_percent: Decimal = Field(description="Largest move while the alert was open")
    reference_price: Decimal
    current_price: Decimal
    observed_at: datetime
    acknowledged_at: datetime | None
    acknowledged_by: str | None
    resolved_at: datetime | None

    @classmethod
    def of(cls, alert: Alert) -> AlertOut:
        return cls.model_validate(alert)


class AlertPageOut(BaseModel):
    items: list[AlertOut]
    total: int
    page: int
    size: int
