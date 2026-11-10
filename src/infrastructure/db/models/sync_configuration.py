from dataclasses import field
from datetime import datetime

from sqlalchemy import Index
from sqlalchemy.orm import Mapped

from domain.enums import IntervalKind
from infrastructure.db.models.base import Base


class SyncConfigurationRow(Base):
    __tablename__ = "sync_configuration"

    ticker: Mapped[str] = field(init=False)
    provider: Mapped[str] = field(init=False)
    interval: Mapped[IntervalKind] = field(init=False)
    date_from: datetime = field(init=False)
    date_to: datetime = field(init=False)

    __table_args__ = (
        Index("ix_sync_configurations_ticker_provider_interval", "ticker", "provider", "interval"),
    )