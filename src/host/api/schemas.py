from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from application import (
    AlertRuleChanges,
    NewAlertRule,
    NewSubscription,
    NewSyncConfiguration,
    SignedIn,
    SubscriptionChanges,
    SyncConfigurationView,
)
from domain.alerts import Alert, AlertRule, AlertTier
from domain.enums import (
    AlertSeverity,
    AlertStatus,
    IntervalKind,
    PriceDirection,
    SyncState,
    SyncStatus,
    UserRole,
)
from domain.models import SyncConfig
from domain.users import Subscription, User


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


Email = Annotated[str, Field(max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
                             examples=["you@example.com"])]


class RegisterIn(BaseModel):
    email: Email
    password: str = Field(min_length=8, max_length=128)


class SignInIn(BaseModel):
    email: Email
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    id: UUID
    email: str
    role: UserRole
    scopes: list[str]

    @classmethod
    def of(cls, user: User) -> UserOut:
        return cls(id=user.id, email=user.email, role=user.role, scopes=list(user.scopes))


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105
    expires_in: int = Field(description="Seconds until the token expires; sign in again then")
    user: UserOut

    @classmethod
    def of(cls, signed_in: SignedIn) -> TokenOut:
        return cls(access_token=signed_in.token.access_token,
                   expires_in=signed_in.token.expires_in, user=UserOut.of(signed_in.user))


class FeedOut(BaseModel):
    id: UUID
    provider: str
    base: str
    quote: str

    @classmethod
    def of(cls, config: SyncConfig) -> FeedOut:
        return cls(id=config.id, provider=config.provider, base=config.base, quote=config.quote)


class SubscriptionIn(BaseModel):
    feed_id: UUID = Field(description="From GET /feeds")
    hour: int = Field(ge=0, le=23, description="Hour of the day to get the email, 0-23")
    timezone: str = Field(default="UTC", max_length=64,
                          description="IANA time zone the hour is in, e.g. Asia/Tbilisi")
    is_active: bool = True

    def to_command(self) -> NewSubscription:
        return NewSubscription(self.feed_id, self.hour, self.timezone, self.is_active)


class SubscriptionPatch(BaseModel):
    hour: int | None = Field(default=None, ge=0, le=23)
    timezone: str | None = Field(default=None, max_length=64)
    is_active: bool | None = None

    def to_changes(self) -> SubscriptionChanges:
        return SubscriptionChanges(self.hour, self.timezone, self.is_active)


class SubscriptionOut(BaseModel):
    id: UUID
    feed: FeedOut
    hour: int
    timezone: str
    is_active: bool
    last_sent_on: date | None

    @classmethod
    def of(cls, sub: Subscription) -> SubscriptionOut:
        return cls(id=sub.id, feed=FeedOut(id=sub.sync_configuration_id, provider=sub.provider,
                                           base=sub.base, quote=sub.quote),
                   hour=sub.hour, timezone=sub.timezone, is_active=sub.is_active,
                   last_sent_on=sub.last_sent_on)
