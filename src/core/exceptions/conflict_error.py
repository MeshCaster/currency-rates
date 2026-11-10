from core.exceptions.app_error import AppError


class ConflictError(AppError):
    status_code, code, title = 409, "conflict", "Conflict"