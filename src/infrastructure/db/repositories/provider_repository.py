from uuid import UUID

from sqlalchemy import exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from domain.enums import IntervalKind, ProviderKind
from domain.models import IntervalCapability, ProviderCapability, ProviderPair
from infrastructure.db.models.provider import ProviderIntervalRow, ProviderPairRow, ProviderRow


class ProviderMapper:
    def to_domain(self, row: ProviderRow) -> ProviderCapability:
        return ProviderCapability(
            id=row.id, key=row.key, display_name=row.display_name, kind=row.kind,
            requires_api_key=row.requires_api_key, is_active=row.is_active,
            intervals=tuple(IntervalCapability(
                interval=i.interval, is_native=i.is_native, history_start=i.history_start,
                history_window_days=i.history_window_days,
                max_points_per_request=i.max_points_per_request) for i in row.intervals))


def _pair(row: ProviderPairRow) -> ProviderPair:
    return ProviderPair(id=row.id, provider_id=row.provider_id, provider=row.provider.key,
                        base=row.base, quote=row.quote, symbol=row.symbol)


class SqlProviderRepository:
    mapper = ProviderMapper()

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_key(self, key: str) -> ProviderCapability | None:
        row = await self._session.scalar(self._select().where(ProviderRow.key == key))
        return self.mapper.to_domain(row) if row is not None else None

    async def list(self, *, kind: ProviderKind | None = None,
                   interval: IntervalKind | None = None, currency: str | None = None,
                   active_only: bool = True) -> list[ProviderCapability]:
        stmt = self._select().order_by(ProviderRow.key)
        if active_only:
            stmt = stmt.where(ProviderRow.is_active)
        if kind is not None:
            stmt = stmt.where(ProviderRow.kind == kind)
        if interval is not None:
            stmt = stmt.where(ProviderRow.intervals.any(ProviderIntervalRow.interval == interval))
        if currency is not None:
            stmt = stmt.where(self._supports(ProviderRow.id, currency))
        rows = (await self._session.scalars(stmt)).all()
        return [self.mapper.to_domain(r) for r in rows]

    async def get_pair(self, provider_id: UUID, base: str, quote: str) -> ProviderPair | None:
        row = await self._session.scalar(select(ProviderPairRow).where(
            ProviderPairRow.provider_id == provider_id, ProviderPairRow.base == base.upper(),
            ProviderPairRow.quote == quote.upper()))
        return _pair(row) if row is not None else None

    async def get_pair_by_id(self, id: UUID) -> ProviderPair | None:
        row = await self._session.get(ProviderPairRow, id)
        return _pair(row) if row is not None else None

    async def pairs(self) -> list[ProviderPair]:
        rows = (await self._session.scalars(
            select(ProviderPairRow).join(ProviderRow)
            .order_by(ProviderRow.key, ProviderPairRow.base, ProviderPairRow.quote))).all()
        return [_pair(r) for r in rows]

    @staticmethod
    def _select():  # type: ignore[no-untyped-def]
        return select(ProviderRow).options(selectinload(ProviderRow.intervals))

    @staticmethod
    def _supports(provider_id, currency: str):  # type: ignore[no-untyped-def]
        code = currency.upper()
        return exists().where(ProviderPairRow.provider_id == provider_id,
                              or_(ProviderPairRow.base == code, ProviderPairRow.quote == code))
