from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from application.ports import AlertRepository
from core.exceptions.not_found_error import NotFoundError
from core.pagination import Page
from domain.alerts import Alert
from domain.enums import AlertSeverity, AlertStatus


def utc_now() -> datetime:
    return datetime.now(UTC)


class AlertService:
    def __init__(self, alerts: AlertRepository,
                 clock: Callable[[], datetime] = utc_now) -> None:
        self._alerts = alerts
        self._clock = clock

    async def list(self, *, status: AlertStatus | None = None,
                   severity: AlertSeverity | None = None, rule_id: UUID | None = None,
                   page: int = 1, size: int = 50) -> Page[Alert]:
        return await self._alerts.search(status=status, severity=severity, rule_id=rule_id,
                                         page=page, size=size)

    async def get(self, id: UUID) -> Alert | None:
        return await self._alerts.get(id)

    async def acknowledge(self, id: UUID, by: str) -> Alert:
        alert = await self._alerts.get(id)
        if alert is None:
            raise NotFoundError(f"No alert {id}")
        alert.acknowledge(by, self._clock())
        await self._alerts.update(alert)
        return alert
