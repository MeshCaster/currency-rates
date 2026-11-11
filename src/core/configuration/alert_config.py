from pydantic import BaseModel, Field


class AlertSettings(BaseModel):

    enabled: bool = True
    interval_seconds: float = Field(default=60.0, gt=0)
    sample_retention_days: int = Field(default=31, ge=1)
    max_concurrency: int = Field(default=4, ge=1)
    timeout_seconds: float = Field(default=50.0, gt=0)

    @property
    def max_window_minutes(self) -> int:
        return self.sample_retention_days * 24 * 60
