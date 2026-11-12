from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence, NamedTuple, Any

from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models.rate import RateRow
from domain.enums import RateKind
from domain.models import Rate
from core.database.repository import SqlAlchemyRepository, upsert


class RateKey(NamedTuple):
    base: str
    quote: str
    source: str
    observed_at: datetime

    @classmethod
    def of(cls, rate: Rate) -> RateKey:
        return cls(rate.base, rate.quote, rate.source, rate.as_of)


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


class RateMapper:
    def to_domain(self, row: RateRow) -> Rate:
        return Rate(base=row.base, quote=row.quote, value=row.value, source=row.source,
                    as_of=_utc(row.observed_at))

    def to_values(self, rate: Rate, kind: RateKind = RateKind.OBSERVATION) -> dict[str, Any]:
        return {"base": rate.base, "quote": rate.quote, "source": rate.source,
                "observed_at": rate.as_of, "value": rate.value, "kind": kind.value}


class SqlRateRepository(SqlAlchemyRepository[Rate, RateKey, RateRow]):
    row_type = RateRow
    mapper = RateMapper()
    id_columns = ("base", "quote", "source", "observed_at")
    version_column = None

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def upsert_many(self, rates: Sequence[Rate]) -> int:
        unique = {RateKey.of(r): r for r in rates}
        if not unique:
            return 0
        return await upsert(self._session, RateRow,
                            [self.mapper.to_values(r) for r in unique.values()],
                            conflict_columns=self.id_columns, update_columns=("value",))

    async def update(self, entity: Rate) -> None:
        raise NotImplementedError("Rates are immutable; store a new observation instead")

    async def delete(self, id: RateKey) -> None:
        raise NotImplementedError("Rate history is append-only; use a retention policy")

    async def provider_series(self, base: str, quote: str, provider: str, *,
                              since: datetime | None = None, limit: int | None = None,
                              newest_first: bool = False) -> list[Rate]:
        criteria = [*self._pair(base, quote),
                    or_(RateRow.source == provider, RateRow.source.like(f"{provider}:%"))]
        if since is not None:
            criteria.append(RateRow.observed_at >= since)
        order = RateRow.observed_at.desc() if newest_first else RateRow.observed_at
        return await self._find(*criteria, order_by=[order], limit=limit)

    @staticmethod
    def _pair(base: str, quote: str) -> tuple[Any, Any]:
        return (RateRow.base == base.upper(), RateRow.quote == quote.upper())
