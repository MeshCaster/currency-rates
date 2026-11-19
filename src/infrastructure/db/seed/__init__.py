from dataclasses import dataclass
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.repository import insert_ignore, upsert
from infrastructure.db.models import (
    CurrencyRow,
    ProviderIntervalRow,
    ProviderPairRow,
    ProviderRow,
    SyncConfigurationRow,
)
from infrastructure.db.seed.catalog import CURRENCIES, PROVIDERS


@dataclass(frozen=True, slots=True)
class CatalogReport:
    currencies: int
    providers: int
    intervals: int
    provider_pairs: int


async def seed_catalog(session: AsyncSession) -> CatalogReport:
    currencies = await upsert(
        session, CurrencyRow,
        [{"code": c.code, "name": c.name, "kind": c.kind, "icon": c.icon} for c in CURRENCIES],
        conflict_columns=["code"], update_columns=["name", "kind", "icon"])
    providers = await upsert(
        session, ProviderRow,
        [{"key": p.key, "display_name": p.display_name, "kind": p.kind,
          "requires_api_key": p.requires_api_key} for p in PROVIDERS],
        conflict_columns=["key"], update_columns=["display_name", "kind", "requires_api_key"])

    ids = await _provider_ids(session)
    intervals = await upsert(
        session, ProviderIntervalRow,
        [{"provider_id": ids[p.key], "interval": i.interval, "is_native": i.is_native,
          "history_start": i.history_start, "history_window_days": i.history_window_days,
          "max_points_per_request": i.max_points_per_request}
         for p in PROVIDERS for i in p.intervals],
        conflict_columns=["provider_id", "interval"],
        update_columns=["is_native", "history_start", "history_window_days",
                        "max_points_per_request"])
    provider_pairs = await upsert(
        session, ProviderPairRow,
        [{"provider_id": ids[p.key], "base": pair.base, "quote": pair.quote,
          "symbol": pair.symbol}
         for p in PROVIDERS for pair in p.pairs],
        conflict_columns=["provider_id", "base", "quote"], update_columns=["symbol"])
    return CatalogReport(currencies, providers, intervals, provider_pairs)


async def seed_dev_sync(session: AsyncSession, today: date) -> int:
    ids = await _provider_ids(session)
    return await insert_ignore(session, SyncConfigurationRow, [
        {"provider_id": ids[p.key], "base": s.base, "quote": s.quote, "interval": s.interval,
         "date_from": today - timedelta(days=s.days_back),
         "options": dict(s.options) if s.options is not None else None,
         "is_active": s.is_active}
        for p in PROVIDERS for s in p.dev_sync])


async def _provider_ids(session: AsyncSession) -> dict[str, UUID]:
    rows = await session.execute(select(ProviderRow.key, ProviderRow.id))
    return {key: id for key, id in rows.tuples()}
