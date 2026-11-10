import os
from functools import lru_cache
from pathlib import Path
from typing import Literal
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

APP_ENV = os.getenv("APP_ENV", "development")

BASE_DIR = Path(__file__).resolve().parent

class DatabaseSettings(BaseModel):
    url: str
    pool_size: int = 5

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BASE_DIR / ".env", BASE_DIR / f".env.{APP_ENV}", BASE_DIR / ".env.local"),
        env_nested_delimiter="__",
        extra="ignore",
    )

    app_env: Literal["development", "staging", "production"] = "development"
    app_name: str = "rate-service"
    debug: bool = False
    database: DatabaseSettings
    api_key: str

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

@lru_cache
def get_settings() -> Settings:
    return Settings()
