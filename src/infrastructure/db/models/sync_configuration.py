from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.identity import EntityBase
from domain.enums import IntervalKind, SyncStatus
from infrastructure.db.models.columns import enum_column
from infrastructure.db.models.provider import ProviderRow


class SyncConfigurationRow(EntityBase):

    __tablename__ = "sync_configurations"

    provider_id: Mapped[UUID] = mapped_column(ForeignKey("providers.id"))
    base: Mapped[str] = mapped_column(String(10))
    quote: Mapped[str] = mapped_column(String(10))
    interval: Mapped[IntervalKind] = mapped_column(enum_column(IntervalKind))
    date_from: Mapped[date]
    date_to: Mapped[date | None]
    synced_until: Mapped[date | None]
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())
    options: Mapped[dict[str, Any] | None]
    last_run_at: Mapped[datetime | None]
    last_status: Mapped[SyncStatus | None] = mapped_column(enum_column(SyncStatus))
    last_error: Mapped[str | None] = mapped_column(Text)

    provider: Mapped[ProviderRow] = relationship(lazy="joined", innerjoin=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["provider_id", "interval"],
            ["provider_intervals.provider_id", "provider_intervals.interval"],
            name="fk_sync_configurations_interval_provider_intervals"),
        ForeignKeyConstraint(
            ["provider_id", "base"],
            ["provider_currencies.provider_id", "provider_currencies.currency_code"],
            name="fk_sync_configurations_base_provider_currencies"),
        ForeignKeyConstraint(
            ["provider_id", "quote"],
            ["provider_currencies.provider_id", "provider_currencies.currency_code"],
            name="fk_sync_configurations_quote_provider_currencies"),
        UniqueConstraint("provider_id", "base", "quote", "interval",
                         name="uq_sync_configurations_provider_pair_interval"),
        CheckConstraint("base <> quote", name="base_differs_from_quote"),
        CheckConstraint("date_to IS NULL OR date_from <= date_to", name="date_range"),
        Index("ix_sync_configurations_active", "synced_until",
              postgresql_where=text("is_active"), sqlite_where=text("is_active")),
    )
