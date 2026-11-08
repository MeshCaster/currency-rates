from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

PriceKind = Literal["spot", "buy", "sell"]


class CoinbasePrice(BaseModel):
    amount: Decimal
    currency: str
    base: str | None = None


class CoinbasePriceResponse(BaseModel):
    data: CoinbasePrice