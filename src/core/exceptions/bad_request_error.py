from core.exceptions.app_error import AppError


class BadRequestError(AppError):
    status_code, code, title = 400, "bad_request", "Bad Request"