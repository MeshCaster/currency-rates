from dataclasses import dataclass, field
from datetime import date
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from domain.enums import UserRole
from domain.errors import InvalidSubscriptionError

USER_SCOPES = ("subscriptions:read", "subscriptions:write")
ADMIN_SCOPES = (*USER_SCOPES, "sync:read", "sync:write", "alerts:read", "alerts:write")
ROLE_SCOPES: dict[UserRole, tuple[str, ...]] = {UserRole.USER: USER_SCOPES,
                                                UserRole.ADMIN: ADMIN_SCOPES}


def normalize_email(email: str) -> str:
    return email.strip().lower()


@dataclass(slots=True)
class User:
    id: UUID
    email: str
    password_hash: str
    role: UserRole = UserRole.USER
    is_active: bool = True
    version: int = field(default=0, compare=False)

    def __post_init__(self) -> None:
        self.email = normalize_email(self.email)

    @property
    def scopes(self) -> tuple[str, ...]:
        return ROLE_SCOPES[self.role]


@dataclass(slots=True)
class Subscription:
    id: UUID
    user_id: UUID
    sync_configuration_id: UUID
    hour: int
    timezone: str = "UTC"
    is_active: bool = True
    last_sent_on: date | None = None
    provider: str = ""
    base: str = ""
    quote: str = ""
    version: int = field(default=0, compare=False)

    def __post_init__(self) -> None:
        if not 0 <= self.hour <= 23:
            raise InvalidSubscriptionError("hour must be between 0 and 23")
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError):
            raise InvalidSubscriptionError(f"unknown time zone {self.timezone!r}") from None

    @property
    def zone(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)
