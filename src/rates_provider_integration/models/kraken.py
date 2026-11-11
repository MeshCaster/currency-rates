from decimal import Decimal
from typing import Any

from pydantic import BaseModel

_KRAKEN_ASSETS = {"BTC": "XBT", "DOGE": "XDG"}

class KrakenTicker(BaseModel):
    a: list[Decimal]
    b: list[Decimal]
    c: list[Decimal]
    o: Decimal

    @property
    def last(self) -> Decimal:
        return self.c[0]

    @property
    def bid(self) -> Decimal:
        return self.b[0]

    @property
    def ask(self) -> Decimal:
        return self.a[0]

    @property
    def mid(self) -> Decimal:
        return (self.bid + self.ask) / 2


class KrakenTickerResponse(BaseModel):
    error: list[str]
    result: dict[str, KrakenTicker] = {}

class KrakenOHLCResponse(BaseModel):
    error: list[str]
    result: dict[str, list[list[Any]] | int] = {}
