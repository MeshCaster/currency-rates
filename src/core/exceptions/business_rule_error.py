from core.exceptions.app_error import AppError


class BusinessRuleError(AppError):
    status_code, code, title = 422, "business_rule_violation", "Unprocessable Content"
