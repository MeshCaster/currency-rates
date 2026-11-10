from core.exceptions.app_error import AppError


class ServiceUnavailableError(AppError):
    status_code, code, title = 503, "service_unavailable", "Service Unavailable"
