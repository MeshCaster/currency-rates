from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence, NamedTuple, Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models.rate import RateRow
from domain.enums import OFFICIAL_KINDS, RateKind
from domain.models import Rate
from core.database.repository import SqlAlchemyRepository, upsert
from core.pagination import Page


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

    async def add_many(self, rates: Sequence[Rate], kind: RateKind = RateKind.OBSERVATION) -> int:
        if not rates:
            return 0
        rows = [self.mapper.to_values(r, kind) for r in rates]
        return await self._insert_ignore(rows)

    async def upsert_many(self, rates: Sequence[Rate]) -> int:
        if not rates:
            return 0
        return await upsert(self._session, RateRow, [self.mapper.to_values(r) for r in rates],
                            conflict_columns=self.id_columns, update_columns=("value",))

    async def add_sync_result(self, accepted: Sequence[Rate], resolved: Rate | None) -> int:
        resolved_key = RateKey.of(resolved) if resolved else None
        rows = [self.mapper.to_values(r, RateKind.RESOLVED if RateKey.of(r) == resolved_key
                                      else RateKind.OBSERVATION)
                for r in accepted]
        if resolved is not None and resolved_key not in {RateKey.of(r) for r in accepted}:
            rows.append(self.mapper.to_values(resolved, RateKind.RESOLVED))
        return await self._insert_ignore(rows) if rows else 0

    async def update(self, entity: Rate) -> None:
        raise NotImplementedError("Rates are immutable; store a new observation instead")

    async def delete(self, id: RateKey) -> None:
        raise NotImplementedError("Rate history is append-only; use a retention policy")

    async def latest_resolved(self, base: str, quote: str) -> Rate | None:
        found = await self._find(*self._pair(base, quote), RateRow.kind.in_(OFFICIAL_KINDS),
                                 order_by=[RateRow.observed_at.desc()], limit=1)
        return found[0] if found else None

    async def latest(self, base: str, quote: str, source: str | None = None) -> Rate | None:
        criteria = list(self._pair(base, quote))
        if source is not None:
            criteria.append(RateRow.source == source)
        found = await self._find(*criteria, order_by=[RateRow.observed_at.desc()], limit=1)
        return found[0] if found else None

    async def latest_by_source(self, base: str, quote: str) -> list[Rate]:
        sub = (select(RateRow.source, func.max(RateRow.observed_at).label("ts"))
               .where(*self._pair(base, quote), RateRow.kind != RateKind.CROSS.value)
               .group_by(RateRow.source).subquery())
        stmt = (select(RateRow)
                .join(sub, (RateRow.source == sub.c.source)
                      & (RateRow.observed_at == sub.c.ts))
                .where(*self._pair(base, quote))
                .order_by(RateRow.source))
        rows = (await self._session.scalars(stmt)).all()
        return [self.mapper.to_domain(r) for r in rows]

    async def list_pairs(self, include_cross: bool = False) -> list[tuple[str, str]]:
        kinds = OFFICIAL_KINDS if include_cross else (RateKind.RESOLVED.value,)
        stmt = (select(RateRow.base, RateRow.quote)
                .where(RateRow.kind.in_(kinds))
                .distinct().order_by(RateRow.base, RateRow.quote))
        return [(b, q) for b, q in (await self._session.execute(stmt)).all()]

    async def window(self, base: str, quote: str, since: datetime, until: datetime | None = None,
                     source: str | None = None, official_only: bool = False) -> list[Rate]:
        criteria = [*self._pair(base, quote), RateRow.observed_at >= since]
        if until is not None:
            criteria.append(RateRow.observed_at < until)
        if source is not None:
            criteria.append(RateRow.source == source)
        if official_only:
            criteria.append(RateRow.kind.in_(OFFICIAL_KINDS))
        return await self._find(*criteria, order_by=[RateRow.observed_at])

    async def history(self, base: str, quote: str, page: int = 1, size: int = 50,
                      official_only: bool = True) -> Page[Rate]:
        criteria = list(self._pair(base, quote))
        if official_only:
            criteria.append(RateRow.kind.in_(OFFICIAL_KINDS))
        return await self._page(*criteria, page=page, size=size,
                                order_by=[RateRow.observed_at.desc(), RateRow.source])

    @staticmethod
    def _pair(base: str, quote: str) -> tuple[Any, Any]:
        return (RateRow.base == base.upper(), RateRow.quote == quote.upper())
