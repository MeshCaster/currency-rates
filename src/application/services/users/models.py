from dataclasses import dataclass
from uuid import UUID

from domain.users import Subscription, User


@dataclass(frozen=True, slots=True)
class IssuedToken:
    access_token: str
    expires_in: int


@dataclass(frozen=True, slots=True)
class SignedIn:
    user: User
    token: IssuedToken


@dataclass(frozen=True, slots=True)
class NewSubscription:
    provider_pair_id: UUID
    hour: int
    timezone: str = "UTC"
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class SubscriptionChanges:
    hour: int | None = None
    timezone: str | None = None
    is_active: bool | None = None


@dataclass(frozen=True, slots=True)
class SubscriptionView:
    subscription: Subscription
    collecting: bool
