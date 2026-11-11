from pydantic import BaseModel, Field, SecretStr


class AdminSettings(BaseModel):
    email: str | None = None
    password: SecretStr | None = Field(default=None, min_length=8)
