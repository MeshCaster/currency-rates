from typing import Any

from core.database.errors.base import RepositoryError
from core.exceptions.conflict_error import ConflictError


class ConcurrencyError(RepositoryError, ConflictError):
    code = "concurrency_conflict"

    @classmethod
    def for_(cls, entity: str, id: Any) -> ConcurrencyError:
        return cls(cls._message(entity, id, "was modified concurrently"), entity=entity, id=id)
