from enum import StrEnum


class RateKind(StrEnum):
    OBSERVATION = "observation"
    RESOLVED = "resolved"
    CROSS = "cross"

class IntervalKind(StrEnum):
    DAILY = "daily"
    MONTHLY = "monthly"

OFFICIAL_KINDS = (RateKind.RESOLVED, RateKind.CROSS)
OFFICIAL_INTERVAL_KINDS = (IntervalKind.DAILY, IntervalKind.MONTHLY)
