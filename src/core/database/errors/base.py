from typing import Any

from core.exceptions.app_error import AppError


class RepositoryError(AppError):

    def __init__(self, message: str, *, entity: str | None = None, id: Any = None) -> None:
        super().__init__(message)
        self.entity = entity
        self.id = id

    @classmethod
    def _message(cls, entity: str, id: Any, reason: str) -> str:
        return f"{entity} {id!r} {reason}"
