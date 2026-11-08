from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Rate:

    base: str
    quote: str
    value: Decimal
    source: str
    as_of: datetime
