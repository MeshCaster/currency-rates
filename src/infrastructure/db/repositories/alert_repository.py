from collections.abc import Collection, Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import CursorResult, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.mapper import DataclassMapper
from core.database.repository import SqlAlchemyRepository, insert_ignore
from core.pagination import Page
from domain.alerts import Alert, AlertRule, AlertTier, PriceSample
from domain.enums import AlertSeverity, AlertStatus
from infrastructure.db.models.alert import AlertRow, AlertRuleRow, PriceSampleRow


class AlertRuleMapper:
    def to_domain(self, row: AlertRuleRow) -> AlertRule:
        config = row.sync_configuration
        return AlertRule(
            id=row.id, sync_configuration_id=row.sync_configuration_id, name=row.name,
            window_minutes=row.window_minutes, direction=row.direction,
            tiers=tuple(AlertTier(Decimal(t["threshold_percent"]), AlertSeverity(t["severity"]))
                        for t in row.tiers),
            is_active=row.is_active, provider=config.provider.key, base=config.base,
            quote=config.quote, version=row.version)

    def to_values(self, rule: AlertRule) -> dict[str, Any]:
        return {"id": rule.id, "sync_configuration_id": rule.sync_configuration_id,
                "name": rule.name, "window_minutes": rule.window_minutes,
                "direction": rule.direction,
                "tiers": [{"threshold_percent": str(t.threshold_percent),
                           "severity": t.severity.value} for t in rule.tiers],
                "is_active": rule.is_active, "version": rule.version}


class SqlAlertRuleRepository(SqlAlchemyRepository[AlertRule, UUID, AlertRuleRow]):
    row_type = AlertRuleRow
    mapper = AlertRuleMapper()

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_active(self) -> list[AlertRule]:
        return await self._find(AlertRuleRow.is_active.is_(True),
                                order_by=[AlertRuleRow.sync_configuration_id, AlertRuleRow.id])

    async def search(self, *, sync_configuration_id: UUID | None = None,
                     is_active: bool | None = None, page: int = 1,
                     size: int = 50) -> Page[AlertRule]:
        row = AlertRuleRow
        criteria = []
        if sync_configuration_id is not None:
            criteria.append(row.sync_configuration_id == sync_configuration_id)
        if is_active is not None:
            criteria.append(row.is_active.is_(is_active))
        return await self._page(*criteria, page=page, size=size, order_by=[row.name, row.id])


class SqlAlertRepository(SqlAlchemyRepository[Alert, UUID, AlertRow]):
    row_type = AlertRow
    mapper = DataclassMapper(Alert, AlertRow)

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def unresolved_for(self, rule_ids: Collection[UUID]) -> dict[UUID, Alert]:
        if not rule_ids:
            return {}
        found = await self._find(AlertRow.rule_id.in_(list(rule_ids)),
                                 AlertRow.status != AlertStatus.RESOLVED)
        return {a.rule_id: a for a in found}

    async def search(self, *, status: AlertStatus | None = None,
                     severity: AlertSeverity | None = None, rule_id: UUID | None = None,
                     page: int = 1, size: int = 50) -> Page[Alert]:
        row = AlertRow
        criteria = []
        if status is not None:
            criteria.append(row.status == status)
        if severity is not None:
            criteria.append(row.severity == severity)
        if rule_id is not None:
            criteria.append(row.rule_id == rule_id)
        return await self._page(*criteria, page=page, size=size,
                                order_by=[row.opened_at.desc(), row.id])


class SqlPriceSampleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_many(self, samples: Sequence[PriceSample]) -> int:
        rows = [{"sync_configuration_id": s.sync_configuration_id, "sampled_at": s.sampled_at,
                 "value": s.value} for s in samples]
        return await insert_ignore(self._session, PriceSampleRow, rows)

    async def latest(self, sync_configuration_id: UUID,
                     at_or_before: datetime) -> PriceSample | None:
        row = await self._session.scalar(
            select(PriceSampleRow)
            .where(PriceSampleRow.sync_configuration_id == sync_configuration_id,
                   PriceSampleRow.sampled_at <= at_or_before)
            .order_by(PriceSampleRow.sampled_at.desc()).limit(1))
        return (PriceSample(row.sync_configuration_id, row.sampled_at, row.value)
                if row is not None else None)

    async def prune(self, older_than: datetime) -> int:
        result = cast("CursorResult[Any]", await self._session.execute(
            delete(PriceSampleRow).where(PriceSampleRow.sampled_at < older_than)))
        return max(result.rowcount, 0)
