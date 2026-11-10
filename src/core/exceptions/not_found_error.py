from core.exceptions.app_error import AppError


class NotFoundError(AppError):
    status_code, code, title = 404, "not_found", "Not Found"