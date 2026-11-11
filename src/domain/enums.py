from enum import StrEnum


class RateKind(StrEnum):
    OBSERVATION = "observation"
    RESOLVED = "resolved"
    CROSS = "cross"

class IntervalKind(StrEnum):
    DAILY = "daily"
    MONTHLY = "monthly"

class CurrencyKind(StrEnum):
    FIAT = "fiat"
    CRYPTO = "crypto"
    STABLECOIN = "stablecoin"

class ProviderKind(StrEnum):
    FX = "fx"
    CRYPTO = "crypto"

class SyncStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"

class SyncState(StrEnum):
    PAUSED = "paused"
    PENDING = "pending"
    BACKFILLING = "backfilling"
    LIVE = "live"
    COMPLETED = "completed"
    FAILED = "failed"

OFFICIAL_KINDS = (RateKind.RESOLVED, RateKind.CROSS)
OFFICIAL_INTERVAL_KINDS = (IntervalKind.DAILY, IntervalKind.MONTHLY)
