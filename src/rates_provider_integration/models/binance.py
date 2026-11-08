from decimal import Decimal

from pydantic import BaseModel

class BinanceTicker(BaseModel):
    symbol: str
    price: Decimal
