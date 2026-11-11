from datetime import date
from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint, false, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.audit import AuditedBase
from core.database.identity import IdentityMixin
from domain.enums import IntervalKind, ProviderKind
from infrastructure.db.models.columns import enum_column


class ProviderRow(IdentityMixin, AuditedBase):
    __tablename__ = "providers"

    key: Mapped[str] = mapped_column(String(40), unique=True)
    display_name: Mapped[str] = mapped_column(String(64))
    kind: Mapped[ProviderKind] = mapped_column(enum_column(ProviderKind))
    requires_api_key: Mapped[bool] = mapped_column(default=False, server_default=false())
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())

    intervals: Mapped[list[ProviderIntervalRow]] = relationship(
        back_populates="provider", lazy="raise", order_by="ProviderIntervalRow.interval",
        cascade="all, delete-orphan", passive_deletes=True)


class ProviderIntervalRow(IdentityMixin, AuditedBase):
    __tablename__ = "provider_intervals"

    provider_id: Mapped[UUID] = mapped_column(ForeignKey("providers.id", ondelete="CASCADE"))
    interval: Mapped[IntervalKind] = mapped_column(enum_column(IntervalKind))
    is_native: Mapped[bool]
    history_start: Mapped[date | None]
    history_window_days: Mapped[int | None]
    max_points_per_request: Mapped[int | None]

    provider: Mapped[ProviderRow] = relationship(back_populates="intervals", lazy="raise")

    __table_args__ = (
        UniqueConstraint("provider_id", "interval"),
    )


class ProviderCurrencyRow(IdentityMixin, AuditedBase):
    __tablename__ = "provider_currencies"

    provider_id: Mapped[UUID] = mapped_column(ForeignKey("providers.id", ondelete="CASCADE"))
    currency_code: Mapped[str] = mapped_column(
        String(10), ForeignKey("currencies.code", ondelete="CASCADE", onupdate="CASCADE"))
    provider_code: Mapped[str | None] = mapped_column(String(40))
    available_from: Mapped[date | None]

    __table_args__ = (
        UniqueConstraint("provider_id", "currency_code"),
    )
