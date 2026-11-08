from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol

import httpx


@dataclass(frozen=True, slots=True)
class Rate:
    base: str
    quote: str
    value: Decimal
    source: str
    as_of: datetime


class RateProviderError(Exception):
    def __init__(self, code: int, message: str, details: dict):
        self.code = code
        self.message = message
        self.details = details

class RateProvider(Protocol):
    name: str

    async def get_rate(self, base: str, quote: str) -> Rate: ...


def default_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(10.0, connect=5.0),
        headers={"User-Agent": "myservice/1.0"},
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    )
