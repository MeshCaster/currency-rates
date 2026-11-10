from core.exceptions.app_error import AppError


class ExternalServiceError(AppError):
    status_code, code, title = 502, "external_service_error", "Bad Gateway"
