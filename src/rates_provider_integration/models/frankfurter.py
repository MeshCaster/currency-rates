from datetime import date
from decimal import Decimal

from pydantic import BaseModel

class FrankfurterRate(BaseModel):
    date: date
    base: str
    quote: str
    rate: Decimal