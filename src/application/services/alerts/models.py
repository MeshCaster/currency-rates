from collections.abc import Sequence
from dataclasses import dataclass, field
from uuid import UUID

from domain.alerts import AlertTier
from domain.enums import PriceDirection


@dataclass(frozen=True, slots=True)
class NewAlertRule:
    sync_configuration_id: UUID
    name: str
    window_minutes: int
    tiers: Sequence[AlertTier]
    direction: PriceDirection = PriceDirection.BOTH
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class AlertRuleChanges:
    name: str | None = None
    window_minutes: int | None = None
    tiers: Sequence[AlertTier] | None = None
    direction: PriceDirection | None = None
    is_active: bool | None = None


@dataclass(slots=True)
class AlertTickResult:
    evaluated: int = 0
    skipped: list[str] = field(default_factory=list)
    opened: int = 0
    escalated: int = 0
    resolved: int = 0
