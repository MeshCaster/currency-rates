from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, String, text, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.identity import EntityBase
from core.database.orm import Base
from core.database.types import JsonColumn
from domain.enums import AlertSeverity, AlertStatus, PriceDirection
from infrastructure.db.models.columns import enum_column
from infrastructure.db.models.sync_configuration import SyncConfigurationRow


class AlertRuleRow(EntityBase):
    __tablename__ = "alert_rules"

    sync_configuration_id: Mapped[UUID] = mapped_column(
        ForeignKey("sync_configurations.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(120))
    window_minutes: Mapped[int]
    direction: Mapped[PriceDirection] = mapped_column(enum_column(PriceDirection))
    tiers: Mapped[list[dict[str, Any]]] = mapped_column(JsonColumn(list[dict[str, Any]]))
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())

    sync_configuration: Mapped[SyncConfigurationRow] = relationship(lazy="joined",
                                                                    innerjoin=True)

    __table_args__ = (
        CheckConstraint("window_minutes >= 1", name="window_positive"),
        Index("ix_alert_rules_sync_configuration_id", "sync_configuration_id"),
    )


class AlertRow(EntityBase):
    __tablename__ = "alerts"

    rule_id: Mapped[UUID] = mapped_column(ForeignKey("alert_rules.id", ondelete="CASCADE"))
    severity: Mapped[AlertSeverity] = mapped_column(enum_column(AlertSeverity))
    status: Mapped[AlertStatus] = mapped_column(enum_column(AlertStatus))
    opened_at: Mapped[datetime]
    change_percent: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    peak_change_percent: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    reference_price: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    current_price: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    observed_at: Mapped[datetime]
    acknowledged_at: Mapped[datetime | None]
    acknowledged_by: Mapped[str | None] = mapped_column(String(200))
    resolved_at: Mapped[datetime | None]

    __table_args__ = (
        Index("uq_alerts_rule_id_unresolved", "rule_id", unique=True,
              postgresql_where=text("status <> 'resolved'"),
              sqlite_where=text("status <> 'resolved'")),
        Index("ix_alerts_status_opened_at", "status", "opened_at"),
    )


class PriceSampleRow(Base):
    __tablename__ = "price_samples"

    sync_configuration_id: Mapped[UUID] = mapped_column(
        ForeignKey("sync_configurations.id", ondelete="CASCADE"), primary_key=True)
    sampled_at: Mapped[datetime] = mapped_column(primary_key=True)
    value: Mapped[Decimal] = mapped_column(Numeric(38, 18))

    __table_args__ = (
        Index("ix_price_samples_sampled_at", "sampled_at"),
    )
