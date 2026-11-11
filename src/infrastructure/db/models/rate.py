from datetime import datetime
from decimal import Decimal

from sqlalchemy import Index, Numeric, String, DateTime, func, text
from sqlalchemy.orm import Mapped, mapped_column

from core.database.audit import AuditedBase


class RateRow(AuditedBase):

    __tablename__ = "rates"

    base: Mapped[str] = mapped_column(String(10), primary_key=True)
    quote: Mapped[str] = mapped_column(String(10), primary_key=True)
    source: Mapped[str] = mapped_column(String(40), primary_key=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    value: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    kind: Mapped[str] = mapped_column(String(16), server_default=text("'observation'"))

    __table_args__ = (
        Index("ix_rates_base_quote_observed_at", "base", "quote", "observed_at"),
        Index("ix_rates_base_quote_kind_observed_at", "base", "quote", "kind", "observed_at"),
    )
