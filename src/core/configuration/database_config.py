from pydantic import BaseModel, SecretStr, Field

class DatabaseSettings(BaseModel):
    url: SecretStr | None = None
    echo: bool = False
    pool_size: int = Field(default=5, ge=1)
    max_overflow: int = Field(default=10, ge=0)
    pool_timeout: float = Field(default=30, gt=0)
    pool_recycle: int = Field(default=1800, ge=-1)
    pool_pre_ping: bool = True

    @property
    def enabled(self) -> bool:
        return self.url is not None