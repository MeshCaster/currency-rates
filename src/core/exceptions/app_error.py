from typing import ClassVar, Any


class AppError(Exception):
    status_code: ClassVar[int] = 500
    code: ClassVar[str] = "internal_error"
    title: ClassVar[str] = "Internal Server Error"

    def __init__(
        self,
        detail: str | None = None,
        *,
        code: str | None = None,
        extra: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.detail = detail or self.title
        self.error_code = code or self.code
        self.extra = extra or {}
        self.headers = headers
        super().__init__(self.detail)