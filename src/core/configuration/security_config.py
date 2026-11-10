from typing import Literal, Annotated, Any

from pydantic import BaseModel, SecretStr, Field, field_validator, json
from pydantic_settings import NoDecode

_INSECURE_DEFAULT_SECRET = "insecure-dev-secret-change-me"  # noqa: S105
CsvList = Annotated[list[str], NoDecode]

def _parse_csv_list(value: Any) -> Any:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("["):
            return json.loads(stripped)
        return [item.strip() for item in stripped.split(",") if item.strip()]
    return value

class SecuritySettings(BaseModel):
    secret_key: SecretStr = SecretStr(_INSECURE_DEFAULT_SECRET)
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    access_token_expire_minutes: int = Field(default=15, ge=1)
    jwt_issuer: str | None = None
    jwt_audience: str | None = None
    allowed_hosts: CsvList = ["*"]

    _split = field_validator("allowed_hosts", mode="before")(_parse_csv_list)