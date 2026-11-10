from typing import Any

from core.exceptions.app_error import AppError


class UnauthorizedError(AppError):
    status_code, code, title = 401, "unauthorized", "Unauthorized"

    def __init__(self, detail: str | None = None, **kwargs: Any) -> None:
        kwargs.setdefault("headers", {"WWW-Authenticate": "Bearer"})
        super().__init__(detail, **kwargs)