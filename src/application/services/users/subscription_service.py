import uuid
from collections.abc import Callable
from dataclasses import replace
from uuid import UUID

from application.ports import SubscriptionRepository, SyncConfigurationRepository
from application.services.users.models import NewSubscription, SubscriptionChanges
from core.exceptions.conflict_error import ConflictError
from core.exceptions.not_found_error import NotFoundError
from domain.errors import InvalidSubscriptionError
from domain.users import Subscription


class SubscriptionService:

    def __init__(self, subscriptions: SubscriptionRepository,
                 configs: SyncConfigurationRepository,
                 new_id: Callable[[], UUID] = uuid.uuid7) -> None:
        self._subscriptions = subscriptions
        self._configs = configs
        self._new_id = new_id

    async def list(self, user_id: UUID) -> list[Subscription]:
        return await self._subscriptions.list_for_user(user_id)

    async def create(self, user_id: UUID, new: NewSubscription) -> Subscription:
        config = await self._configs.get(new.sync_configuration_id)
        if config is None or not config.is_active:
            raise InvalidSubscriptionError(f"no rate feed {new.sync_configuration_id}")
        if await self._subscriptions.exists_for(user_id, config.id):
            raise ConflictError(f"already subscribed to {config.provider} "
                                f"{config.base}/{config.quote}", code="already_subscribed")
        subscription = Subscription(
            id=self._new_id(), user_id=user_id, sync_configuration_id=config.id,
            hour=new.hour, timezone=new.timezone, is_active=new.is_active,
            provider=config.provider, base=config.base, quote=config.quote)
        await self._subscriptions.add(subscription)
        return subscription

    async def update(self, user_id: UUID, id: UUID,
                     changes: SubscriptionChanges) -> Subscription:
        subscription = await self._owned(user_id, id)
        updated = replace(
            subscription,
            hour=subscription.hour if changes.hour is None else changes.hour,
            timezone=changes.timezone or subscription.timezone,
            is_active=subscription.is_active if changes.is_active is None
            else changes.is_active)
        await self._subscriptions.update(updated)
        return updated

    async def delete(self, user_id: UUID, id: UUID) -> None:
        await self._owned(user_id, id)
        await self._subscriptions.delete(id)

    async def _owned(self, user_id: UUID, id: UUID) -> Subscription:
        subscription = await self._subscriptions.get(id)
        if subscription is None or subscription.user_id != user_id:
            raise NotFoundError(f"No subscription {id}")
        return subscription
