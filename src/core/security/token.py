import uuid
from datetime import timedelta, datetime, UTC
from typing import Iterable, Any

import jwt
from pydantic import Field, BaseModel

from core.configuration.security_config import SecuritySettings
from core.exceptions.unauthorized_error import UnauthorizedError


class TokenPayload(BaseModel):
    sub: str
    exp: int
    iat: int
    jti: str
    type: str = "access"
    scopes: list[str] = Field(default_factory=list)


def create_access_token(
    subject: str,
    settings: SecuritySettings,
    *,
    scopes: Iterable[str] = (),
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(UTC)
    expire = now + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    claims: dict[str, Any] = {
        **(extra_claims or {}),
        "sub": subject,
        "iat": now,
        "nbf": now,
        "exp": expire,
        "jti": uuid.uuid4().hex,
        "type": "access",
        "scopes": list(scopes),
    }
    if settings.jwt_issuer:
        claims["iss"] = settings.jwt_issuer
    if settings.jwt_audience:
        claims["aud"] = settings.jwt_audience
    return jwt.encode(
        claims, settings.secret_key.get_secret_value(), algorithm=settings.jwt_algorithm
    )


def decode_access_token(token: str, settings: SecuritySettings) -> TokenPayload:
    try:
        claims = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            leeway=10,
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Token has expired", code="token_expired") from exc
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError("Invalid token", code="invalid_token") from exc

    payload = TokenPayload.model_validate(claims)
    if payload.type != "access":
        raise UnauthorizedError("Wrong token type", code="invalid_token")
    return payload