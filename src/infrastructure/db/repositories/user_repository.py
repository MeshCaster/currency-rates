from typing import Any
from uuid import UUID

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
        config = row.sync_configuration
        return Subscription(
            id=row.id, user_id=row.user_id, sync_configuration_id=row.sync_configuration_id,
            hour=row.hour, timezone=row.timezone, is_active=row.is_active,
            last_sent_on=row.last_sent_on, provider=config.provider.key, base=config.base,
            quote=config.quote, version=row.version)

    def to_values(self, sub: Subscription) -> dict[str, Any]:
        return {"id": sub.id, "user_id": sub.user_id,
                "sync_configuration_id": sub.sync_configuration_id, "hour": sub.hour,
                "timezone": sub.timezone, "is_active": sub.is_active,
                "last_sent_on": sub.last_sent_on, "version": sub.version}


class SqlSubscriptionRepository(SqlAlchemyRepository[Subscription, UUID, SubscriptionRow]):
    row_type = SubscriptionRow
    mapper = SubscriptionMapper()

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def add(self, entity: Subscription) -> None:
        await super().add(entity)
        row = await self._session.get(SubscriptionRow, entity.id)
        if row is not None:
            self._session.expunge(row)

    async def list_for_user(self, user_id: UUID) -> list[Subscription]:
        return await self._find(SubscriptionRow.user_id == user_id,
                                order_by=[SubscriptionRow.created_at, SubscriptionRow.id])

    async def exists_for(self, user_id: UUID, sync_configuration_id: UUID) -> bool:
        return bool(await self._find(SubscriptionRow.user_id == user_id,
                                     SubscriptionRow.sync_configuration_id == sync_configuration_id,
                                     limit=1))
