from core.exceptions.app_error import AppError


class RateLimitedError(AppError):
    status_code, code, title = 429, "rate_limited", "Too Many Requests"
