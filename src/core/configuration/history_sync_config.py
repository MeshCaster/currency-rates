from pydantic import BaseModel, Field


class HistorySyncSettings(BaseModel):

    enabled: bool = True
    interval_seconds: float = Field(default=60.0, gt=0)
    max_concurrency: int = Field(default=4, ge=1)
    per_provider_concurrency: int = Field(default=2, ge=1)
    config_timeout_seconds: float = Field(default=120.0, gt=0)
