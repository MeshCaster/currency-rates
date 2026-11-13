from datetime import date
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    UniqueConstraint,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.identity import EntityBase
from domain.enums import UserRole
from infrastructure.db.models.columns import enum_column
from infrastructure.db.models.provider import ProviderPairRow


class UserRow(EntityBase):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(enum_column(UserRole))
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())


class SubscriptionRow(EntityBase):
    __tablename__ = "subscriptions"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    provider_pair_id: Mapped[UUID] = mapped_column(ForeignKey("provider_pairs.id"))
    hour: Mapped[int] = mapped_column(SmallInteger)
    timezone: Mapped[str] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())
    last_sent_on: Mapped[date | None]

    pair: Mapped[ProviderPairRow] = relationship(lazy="joined", innerjoin=True)

    __table_args__ = (
        UniqueConstraint("user_id", "provider_pair_id", name="uq_subscriptions_user_pair"),
        CheckConstraint("hour BETWEEN 0 AND 23", name="hour_of_day"),
        Index("ix_subscriptions_provider_pair_id", "provider_pair_id"),
    )
