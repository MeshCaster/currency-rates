from pydantic import BaseModel, Field


class HttpClientSettings(BaseModel):
    timeout: float = Field(default=10.0, gt=0)
    connect_retries: int = Field(default=2, ge=0)
    max_connections: int = Field(default=100, ge=1)
    max_keepalive_connections: int = Field(default=20, ge=0)
