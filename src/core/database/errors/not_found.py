from typing import Any

from core.database.errors.base import RepositoryError
from core.exceptions.not_found_error import NotFoundError as HttpNotFoundError


class NotFoundError(RepositoryError, HttpNotFoundError, LookupError):
    @classmethod
    def for_(cls, entity: str, id: Any) -> NotFoundError:
        return cls(cls._message(entity, id, "not found"), entity=entity, id=id)
