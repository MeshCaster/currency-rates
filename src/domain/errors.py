from core.exceptions.business_rule_error import BusinessRuleError


class DomainError(BusinessRuleError):
    pass


class UnsupportedSyncError(DomainError):
    pass


class InvalidSyncConfigurationError(DomainError):
    pass


class InvalidAlertRuleError(DomainError):
    pass


class AlertStateError(DomainError):
    pass


class InvalidSubscriptionError(DomainError):
    pass
