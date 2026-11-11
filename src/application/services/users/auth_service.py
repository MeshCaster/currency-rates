import uuid
from collections.abc import Callable
from enum import StrEnum
from functools import lru_cache
from uuid import UUID

from anyio import to_thread

from application.ports import UserRepository
from application.services.users.models import IssuedToken, SignedIn
from core.exceptions.conflict_error import ConflictError
from core.exceptions.unauthorized_error import UnauthorizedError
from core.security.crypto import hash_password, hash_password_async, verify_password_async
from domain.enums import UserRole
from domain.users import User

type TokenIssuer = Callable[[User], IssuedToken]


class AdminSeedOutcome(StrEnum):
    CREATED = "created"
    PROMOTED = "promoted"
    UNCHANGED = "unchanged"


class AuthService:

    def __init__(self, users: UserRepository, issue_token: TokenIssuer | None = None,
                 new_id: Callable[[], UUID] = uuid.uuid7) -> None:
        self._users = users
        self._issue_token = issue_token
        self._new_id = new_id

    async def register(self, email: str, password: str) -> User:
        if await self._users.get_by_email(email) is not None:
            raise ConflictError("this email is already registered", code="email_taken")
        user = User(self._new_id(), email, await hash_password_async(password))
        await self._users.add(user)
        return user

    async def sign_in(self, email: str, password: str) -> SignedIn:
        user = await self._users.get_by_email(email)
        valid = await verify_password_async(password, user.password_hash if user else
                                            await to_thread.run_sync(_dummy_hash))
        if user is None or not valid or not user.is_active:
            raise UnauthorizedError("wrong email or password", code="invalid_credentials")
        if self._issue_token is None:
            raise RuntimeError("AuthService was built without a token issuer")
        return SignedIn(user, self._issue_token(user))

    async def current_user(self, id: UUID) -> User:
        user = await self._users.get(id)
        if user is None or not user.is_active:
            raise UnauthorizedError("this account no longer exists or is disabled",
                                    code="inactive_account")
        return user

    async def ensure_admin(self, email: str, password: str) -> AdminSeedOutcome:
        user = await self._users.get_by_email(email)
        if user is None:
            await self._users.add(User(self._new_id(), email, await hash_password_async(password),
                                       role=UserRole.ADMIN))
            return AdminSeedOutcome.CREATED
        if user.role is UserRole.ADMIN:
            return AdminSeedOutcome.UNCHANGED
        user.role = UserRole.ADMIN
        await self._users.update(user)
        return AdminSeedOutcome.PROMOTED


@lru_cache(maxsize=1)
def _dummy_hash() -> str:
    return hash_password(uuid.uuid4().hex)
