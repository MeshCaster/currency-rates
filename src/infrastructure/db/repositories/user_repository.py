from collections.abc import Collection
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.mapper import DataclassMapper
from core.database.repository import SqlAlchemyRepository
from domain.users import Subscription, User, normalize_email
from infrastructure.db.models.user import SubscriptionRow, UserRow


class SqlUserRepository(SqlAlchemyRepository[User, UUID, UserRow]):
    row_type = UserRow
    mapper = DataclassMapper(User, UserRow)

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_email(self, email: str) -> User | None:
        return await self._find_one(UserRow.email == normalize_email(email))


class SubscriptionMapper:
    def to_domain(self, row: SubscriptionRow) -> Subscription:
        pair = row.pair
        return Subscription(
            id=row.id, user_id=row.user_id, provider_pair_id=row.provider_pair_id,
            hour=row.hour, timezone=row.timezone, is_active=row.is_active,
            last_sent_on=row.last_sent_on, provider=pair.provider.key, base=pair.base,
            quote=pair.quote, version=row.version)

    def to_values(self, sub: Subscription) -> dict[str, Any]:
        return {"id": sub.id, "user_id": sub.user_id,
                "provider_pair_id": sub.provider_pair_id, "hour": sub.hour,
                "timezone": sub.timezone, "is_active": sub.is_active,
                "last_sent_on": sub.last_sent_on, "version": sub.version}


class SqlSubscriptionRepository(SqlAlchemyRepository[Subscription, UUID, SubscriptionRow]):
    row_type = SubscriptionRow
    mapper = SubscriptionMapper()

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_for_user(self, user_id: UUID) -> list[Subscription]:
        return await self._find(SubscriptionRow.user_id == user_id,
                                order_by=[SubscriptionRow.created_at, SubscriptionRow.id])

    async def exists_for(self, user_id: UUID, provider_pair_id: UUID) -> bool:
        return bool(await self._find(SubscriptionRow.user_id == user_id,
                                     SubscriptionRow.provider_pair_id == provider_pair_id,
                                     limit=1))

    async def list_deliverable(self) -> list[tuple[Subscription, str]]:
        stmt = (select(SubscriptionRow, UserRow.email)
                .join(UserRow, UserRow.id == SubscriptionRow.user_id)
                .where(SubscriptionRow.is_active, UserRow.is_active)
                .order_by(UserRow.email, SubscriptionRow.id))
        rows = (await self._session.execute(stmt)).all()
        return [(self.mapper.to_domain(row), email) for row, email in rows]

    async def mark_sent(self, ids: Collection[UUID], on: date) -> None:
        if ids:
            await self._session.execute(
                update(SubscriptionRow).where(SubscriptionRow.id.in_(list(ids)))
                .values(last_sent_on=on).execution_options(synchronize_session=False))
