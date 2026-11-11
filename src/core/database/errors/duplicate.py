from typing import Any

from core.database.errors.base import RepositoryError
from core.exceptions.conflict_error import ConflictError


class DuplicateError(RepositoryError, ConflictError):
    code = "duplicate"

    @classmethod
    def for_(cls, entity: str, id: Any) -> DuplicateError:
        return cls(cls._message(entity, id, "already exists"), entity=entity, id=id)
