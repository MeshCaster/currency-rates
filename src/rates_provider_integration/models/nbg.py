from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

GEL = "GEL"

class NBGRate(BaseModel):
    code: str
    quantity: int
    rate: Decimal
    name: str
    diff: Decimal
    date: datetime
    valid_from: datetime = Field(alias="validFromDate")

    @property
    def rate_per_unit(self) -> Decimal:
        return self.rate / self.quantity

class NBGRatesResponse(BaseModel):
    date: datetime
    rates: list[NBGRate] = Field(alias="currencies")
