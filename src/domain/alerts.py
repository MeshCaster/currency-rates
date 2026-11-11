from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from itertools import pairwise
from uuid import UUID

from domain.enums import AlertSeverity, AlertStatus, PriceDirection
from domain.errors import AlertStateError, InvalidAlertRuleError


@dataclass(frozen=True, slots=True)
class AlertTier:
    threshold_percent: Decimal
    severity: AlertSeverity


@dataclass(frozen=True, slots=True)
class PriceSample:
    sync_configuration_id: UUID
    sampled_at: datetime
    value: Decimal


@dataclass(frozen=True, slots=True)
class PriceMove:
    reference: Decimal
    reference_at: datetime
    current: Decimal
    current_at: datetime

    @property
    def change_percent(self) -> Decimal:
        return (self.current - self.reference) / self.reference * 100


@dataclass(slots=True)
class AlertRule:

    id: UUID
    sync_configuration_id: UUID
    name: str
    window_minutes: int
    tiers: tuple[AlertTier, ...]
    direction: PriceDirection = PriceDirection.BOTH
    is_active: bool = True
    provider: str = ""
    base: str = ""
    quote: str = ""
    version: int = field(default=0, compare=False)

    def __post_init__(self) -> None:
        self.tiers = tuple(sorted(self.tiers, key=lambda t: t.threshold_percent))
        if self.window_minutes < 1:
            raise InvalidAlertRuleError("window_minutes must be at least 1")
        if not self.tiers:
            raise InvalidAlertRuleError("a rule needs at least one tier")
        if any(t.threshold_percent <= 0 for t in self.tiers):
            raise InvalidAlertRuleError("tier thresholds must be above 0%")
        for lower, higher in pairwise(self.tiers):
            if higher.threshold_percent == lower.threshold_percent:
                raise InvalidAlertRuleError(
                    f"two tiers share the {lower.threshold_percent}% threshold")
            if higher.severity.rank <= lower.severity.rank:
                raise InvalidAlertRuleError(
                    "a higher threshold needs a more severe tier "
                    f"({higher.threshold_percent}% is {higher.severity}, "
                    f"{lower.threshold_percent}% is {lower.severity})")

    @property
    def window(self) -> timedelta:
        return timedelta(minutes=self.window_minutes)

    def tier_for(self, move: PriceMove) -> AlertTier | None:
        change = move.change_percent
        if self.direction is PriceDirection.UP:
            size = change
        elif self.direction is PriceDirection.DOWN:
            size = -change
        else:
            size = abs(change)
        reached = [t for t in self.tiers if size >= t.threshold_percent]
        return reached[-1] if reached else None


class AlertChange(StrEnum):
    UPDATED = "updated"
    ESCALATED = "escalated"
    RESOLVED = "resolved"


@dataclass(slots=True)
class Alert:
    id: UUID
    rule_id: UUID
    severity: AlertSeverity
    status: AlertStatus
    opened_at: datetime
    change_percent: Decimal
    peak_change_percent: Decimal
    reference_price: Decimal
    current_price: Decimal
    observed_at: datetime
    acknowledged_at: datetime | None = None
    acknowledged_by: str | None = None
    resolved_at: datetime | None = None
    version: int = field(default=0, compare=False)

    @classmethod
    def open(cls, id: UUID, rule: AlertRule, tier: AlertTier, move: PriceMove) -> Alert:
        change = move.change_percent
        return cls(id=id, rule_id=rule.id, severity=tier.severity, status=AlertStatus.OPEN,
                   opened_at=move.current_at, change_percent=change, peak_change_percent=change,
                   reference_price=move.reference, current_price=move.current,
                   observed_at=move.current_at)

    @property
    def is_resolved(self) -> bool:
        return self.status is AlertStatus.RESOLVED

    def observe(self, tier: AlertTier | None, move: PriceMove) -> AlertChange:
        change = move.change_percent
        self.change_percent = change
        self.reference_price, self.current_price = move.reference, move.current
        self.observed_at = move.current_at
        if abs(change) > abs(self.peak_change_percent):
            self.peak_change_percent = change
        if tier is None:
            self.status, self.resolved_at = AlertStatus.RESOLVED, move.current_at
            return AlertChange.RESOLVED
        if tier.severity.rank > self.severity.rank:
            self.severity, self.status = tier.severity, AlertStatus.OPEN
            self.acknowledged_at = self.acknowledged_by = None
            return AlertChange.ESCALATED
        return AlertChange.UPDATED

    def acknowledge(self, by: str, at: datetime) -> None:
        if self.is_resolved:
            raise AlertStateError("a resolved alert can't be acknowledged")
        self.status, self.acknowledged_at, self.acknowledged_by = AlertStatus.ACKNOWLEDGED, at, by
