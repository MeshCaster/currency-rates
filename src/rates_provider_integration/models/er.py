from datetime import datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ERRatesResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    result: str
    error_type: str | None = Field(default=None, alias="error-type")
    base_code: str | None = None
    time_last_update_unix: int | None = None
    time_next_update_unix: int | None = None
    time_eol_unix: int = 0
    rates: dict[str, Decimal] = Field(default_factory=dict)

    @property
    def last_update(self) -> datetime:
        return datetime.fromtimestamp(self.time_last_update_unix or 0, tz=timezone.utc)

    @property
    def next_update(self) -> datetime:
        return datetime.fromtimestamp(self.time_next_update_unix or 0, tz=timezone.utc)
