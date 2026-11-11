from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from core.database.orm import Base
from core.database.types import UtcDateTime, utc_now


class AuditMixin:

    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), default=utc_now, server_default=func.now(), sort_order=1000)
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), default=utc_now, onupdate=utc_now, server_default=func.now(),
        sort_order=1001)


class AuditedBase(AuditMixin, Base):
    __abstract__ = True
