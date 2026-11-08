from typing import Any

from infrastructure.db.errors.base import RepositoryError


class NotFoundError(RepositoryError, LookupError):
    @classmethod
    def for_(cls, entity: str, id: Any) -> "NotFoundError":
        return cls(cls._message(entity, id, "not found"), entity=entity, id=id)
