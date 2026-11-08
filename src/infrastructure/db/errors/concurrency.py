from typing import Any

from infrastructure.db.errors.base import RepositoryError


class ConcurrencyError(RepositoryError):
    @classmethod
    def for_(cls, entity: str, id: Any) -> "ConcurrencyError":
        return cls(cls._message(entity, id, "was modified concurrently"), entity=entity, id=id)
