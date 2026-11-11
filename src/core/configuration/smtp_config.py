from typing import Literal

from pydantic import BaseModel, Field, SecretStr


class SmtpSettings(BaseModel):
    host: str | None = None
    port: int = Field(default=587, ge=1, le=65535)
    security: Literal["starttls", "ssl", "none"] = "starttls"
    username: str | None = None
    password: SecretStr | None = None
    from_address: str = "Currency Rates <no-reply@localhost>"
    timeout_seconds: float = Field(default=30.0, gt=0)


class NotificationSettings(BaseModel):
    enabled: bool = True
    interval_seconds: float = Field(default=60.0, gt=0)
    catch_up_hours: int = Field(default=3, ge=1, le=23)
    timeout_seconds: float = Field(default=300.0, gt=0)
