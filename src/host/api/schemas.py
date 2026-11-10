from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class RateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    base: str
    quote: str
    value: Decimal
    source: str
    as_of: datetime


class RateHistoryOut(BaseModel):
    items: list[RateOut]
    total: int
    page: int
    size: int


class SyncFailureOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    base: str
    quote: str
    error: str


class SyncResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    fetched: int
    stored: int
    failures: list[SyncFailureOut]
