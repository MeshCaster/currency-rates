import os
from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import SettingsConfigDict, BaseSettings

from core.configuration.cors_config import CorsSettings
from core.configuration.database_config import DatabaseSettings
from core.configuration.http_client_config import HttpClientSettings
from core.configuration.log_config import LogSettings
from core.configuration.otel_config import OtelSettings
from core.configuration.rate_sync_config import RateSyncSettings
from core.configuration.security_config import SecuritySettings, _INSECURE_DEFAULT_SECRET
from core.constants import Environment, LogFormat


def _env_files() -> tuple[str, ...]:
    env = os.getenv("APP_ENV", Environment.DEVELOPMENT).lower()
    files = [".env", f".env.{env}"]
    if env != Environment.TEST:
        files.append(".env.local")
    return tuple(files)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_files(),
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
        validate_default=True,
    )

    app_name: str = "fastapi-practice-currency-rates"
    app_version: str = "0.1.0"
    app_env: Environment = Environment.DEVELOPMENT
    debug: bool = False
    api_prefix: str = "/api/v1"
    root_path: str = ""
    docs_enabled: bool | None = None

    log: LogSettings = Field(default_factory=LogSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    cors: CorsSettings = Field(default_factory=CorsSettings)
    http_client: HttpClientSettings = Field(default_factory=HttpClientSettings)
    otel: OtelSettings = Field(default_factory=OtelSettings)
    rate_sync: RateSyncSettings = Field(default_factory=RateSyncSettings)

    @property
    def is_development(self) -> bool:
        return self.app_env is Environment.DEVELOPMENT

    @property
    def is_test(self) -> bool:
        return self.app_env is Environment.TEST

    @property
    def is_production(self) -> bool:
        return self.app_env is Environment.PRODUCTION

    @property
    def is_deployed(self) -> bool:
        return self.app_env in (Environment.STAGING, Environment.PRODUCTION)

    @property
    def show_docs(self) -> bool:
        return self.docs_enabled if self.docs_enabled is not None else not self.is_production

    @property
    def log_format(self) -> LogFormat:
        if self.log.format is not None:
            return self.log.format
        return LogFormat.TEXT if self.is_development else LogFormat.JSON

    @model_validator(mode="after")
    def _check_deployed_environment(self) -> Settings:
        if not self.is_deployed:
            return self
        problems: list[str] = []
        secret = self.security.secret_key.get_secret_value()
        if secret == _INSECURE_DEFAULT_SECRET or len(secret) < 32:
            problems.append("SECURITY__SECRET_KEY must be a random value of at least 32 chars")
        if self.debug:
            problems.append("DEBUG must be false")
        if "*" in self.cors.allow_origins and self.cors.allow_credentials:
            problems.append("CORS wildcard origin cannot be combined with credentials")
        if problems:
            raise ValueError(f"Invalid configuration for '{self.app_env}': " + "; ".join(problems))
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
