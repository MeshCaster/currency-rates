from core.exceptions.app_error import AppError


class ForbiddenError(AppError):
    status_code, code, title = 403, "forbidden", "Forbidden"