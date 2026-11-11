from sqlalchemy import text
from sqlalchemy.orm import Mapped, mapped_column


class VersionMixin:
    version: Mapped[int] = mapped_column(default=1, server_default=text("1"), sort_order=999)
