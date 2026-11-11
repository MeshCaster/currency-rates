from dataclasses import replace
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import and_, or_, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.errors import ConcurrencyError, NotFoundError
from core.database.repository import SqlAlchemyRepository
from core.database.types import utc_now
from domain.enums import SyncStatus
from domain.models import SyncConfig
from infrastructure.db.models.provider import ProviderRow
from infrastructure.db.models.sync_configuration import SyncConfigurationRow

_MAX_ERROR_LENGTH = 2000


class SyncConfigMapper:
    def to_domain(self, row: SyncConfigurationRow) -> SyncConfig:
        return SyncConfig(
            id=row.id, provider_id=row.provider_id, provider=row.provider.key,
            base=row.base, quote=row.quote, interval=row.interval,
            date_from=row.date_from, date_to=row.date_to, synced_until=row.synced_until,
            is_active=row.is_active, options=dict(row.options) if row.options is not None else None,
            last_run_at=row.last_run_at, last_status=row.last_status, last_error=row.last_error,
            version=row.version)

    def to_values(self, config: SyncConfig) -> dict[str, Any]:
        return {"id": config.id, "provider_id": config.provider_id,
                "base": config.base.upper(), "quote": config.quote.upper(),
                "interval": config.interval, "date_from": config.date_from,
                "date_to": config.date_to, "synced_until": config.synced_until,
                "is_active": config.is_active, "options": config.options,
                "last_run_at": config.last_run_at, "last_status": config.last_status,
                "last_error": config.last_error, "version": config.version}


class SqlSyncConfigurationRepository(
        SqlAlchemyRepository[SyncConfig, UUID, SyncConfigurationRow]):
    row_type = SyncConfigurationRow
    mapper = SyncConfigMapper()

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def add(self, entity: SyncConfig) -> None:
        await super().add(entity)
        row = await self._session.get(SyncConfigurationRow, entity.id)
        if row is not None:
            self._session.expunge(row)

    async def list_due(self, as_of: date) -> list[SyncConfig]:
        row = SyncConfigurationRow
        behind = and_(row.synced_until < as_of,
                      or_(row.date_to.is_(None), row.synced_until < row.date_to))
        return await self._find(
            row.is_active,
            row.provider.has(ProviderRow.is_active),
            row.date_from <= as_of,
            or_(row.synced_until.is_(None), behind),
            order_by=[row.synced_until.asc().nulls_first(), row.id])

    async def advance(self, config: SyncConfig, synced_until: date) -> SyncConfig:
        values = {"synced_until": synced_until, "last_run_at": utc_now(),
                  "last_status": SyncStatus.SUCCEEDED, "last_error": None,
                  "version": config.version + 1}
        result = await self._session.execute(
            update(SyncConfigurationRow)
            .where(SyncConfigurationRow.id == config.id,
                   SyncConfigurationRow.version == config.version)
            .values(**values).execution_options(synchronize_session=False))
        if result.rowcount == 0:
            if await self.exists(config.id):
                raise ConcurrencyError.for_(SyncConfigurationRow.__name__, config.id)
            raise NotFoundError.for_(SyncConfigurationRow.__name__, config.id)
        return replace(config, **values)

    async def record_failure(self, id: UUID, error: str) -> None:
        result = await self._session.execute(
            update(SyncConfigurationRow).where(SyncConfigurationRow.id == id)
            .values(last_run_at=utc_now(), last_status=SyncStatus.FAILED,
                    last_error=error[:_MAX_ERROR_LENGTH])
            .execution_options(synchronize_session=False))
        if result.rowcount == 0:
            raise NotFoundError.for_(SyncConfigurationRow.__name__, id)
