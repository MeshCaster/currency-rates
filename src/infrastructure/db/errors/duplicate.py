from typing import Any

from infrastructure.db.errors.base import RepositoryError


class DuplicateError(RepositoryError):
    @classmethod
    def for_(cls, entity: str, id: Any) -> "DuplicateError":
        return cls(cls._message(entity, id, "already exists"), entity=entity, id=id)
