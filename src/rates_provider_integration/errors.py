from core.exceptions.external_service_error import ExternalServiceError


class IntegrationError(ExternalServiceError):
    pass


class RateProviderError(IntegrationError):

    def __init__(self, message: str, *, code: int | None = None, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.upstream_status = code
        self.details = details
