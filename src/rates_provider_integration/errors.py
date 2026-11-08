from common.errors import AppError


class IntegrationError(AppError):
    pass


class RateProviderError(IntegrationError):
    def __init__(self, message: str, *, code: int | None = None, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details
