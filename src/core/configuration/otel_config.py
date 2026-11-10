from typing import Literal

from pydantic import BaseModel, Field


class OtelSettings(BaseModel):
    enabled: bool = False
    exporter: Literal["otlp", "console"] = "otlp"
    endpoint: str | None = None
    service_name: str | None = None
    sample_ratio: float = Field(default=1.0, ge=0.0, le=1.0)
