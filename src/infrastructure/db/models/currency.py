from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from core.database.audit import AuditedBase
from core.database.identity import IdentityMixin
from domain.enums import CurrencyKind
from infrastructure.db.models.columns import enum_column


class CurrencyRow(IdentityMixin, AuditedBase):
    __tablename__ = "currencies"

    code: Mapped[str] = mapped_column(String(10), unique=True)
    name: Mapped[str] = mapped_column(String(64))
    kind: Mapped[CurrencyKind] = mapped_column(enum_column(CurrencyKind))
    icon: Mapped[str | None] = mapped_column(String(255))
