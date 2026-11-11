import uuid

from sqlalchemy.orm import Mapped, mapped_column

from core.database.audit import AuditedBase
from core.database.version import VersionMixin


class IdentityMixin:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7, sort_order=-1)


class EntityBase(IdentityMixin, VersionMixin, AuditedBase):

    __abstract__ = True
