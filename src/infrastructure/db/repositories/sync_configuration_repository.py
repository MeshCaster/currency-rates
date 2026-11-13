from dataclasses import replace
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import and_, or_, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.errors import ConcurrencyError, NotFoundError
from core.database.repository import SqlAlchemyRepository
from core.database.types import utc_now
from core.pagination import Page
from domain.enums import IntervalKind, SyncStatus
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

    async def exists_for(self, provider_id: UUID, base: str, quote: str,
                         interval: IntervalKind) -> bool:
        row = SyncConfigurationRow
        found = await self._find(row.provider_id == provider_id, row.base == base.upper(),
                                 row.quote == quote.upper(), row.interval == interval, limit=1)
        return bool(found)

    async def find_for(self, provider_id: UUID, base: str, quote: str,
                       interval: IntervalKind) -> SyncConfig | None:
        row = SyncConfigurationRow
        return await self._find_one(row.provider_id == provider_id, row.base == base.upper(),
                                    row.quote == quote.upper(), row.interval == interval)

    async def list_active(self, interval: IntervalKind) -> list[SyncConfig]:
        row = SyncConfigurationRow
        return await self._find(row.is_active.is_(True), row.interval == interval,
                                row.provider.has(ProviderRow.is_active),
                                order_by=[row.base, row.quote, row.id])

    async def search(self, *, provider: str | None = None, is_active: bool | None = None,
                     page: int = 1, size: int = 50) -> Page[SyncConfig]:
        row = SyncConfigurationRow
        criteria = []
        if provider is not None:
            criteria.append(row.provider.has(ProviderRow.key == provider))
        if is_active is not None:
            criteria.append(row.is_active.is_(is_active))
        return await self._page(*criteria, page=page, size=size,
                                order_by=[row.base, row.quote, row.interval, row.id])

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
