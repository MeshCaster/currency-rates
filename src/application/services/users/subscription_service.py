import uuid
from collections.abc import Callable
from dataclasses import replace
from uuid import UUID

from application.ports import ProviderCatalog, SubscriptionRepository, SyncConfigurationRepository
from application.services.users.models import NewSubscription, SubscriptionChanges, SubscriptionView
from core.exceptions.conflict_error import ConflictError
from core.exceptions.not_found_error import NotFoundError
from domain.enums import IntervalKind
from domain.errors import InvalidSubscriptionError
from domain.users import Subscription


class SubscriptionService:

    def __init__(self, subscriptions: SubscriptionRepository,
                 configs: SyncConfigurationRepository, catalog: ProviderCatalog,
                 new_id: Callable[[], UUID] = uuid.uuid7) -> None:
        self._subscriptions = subscriptions
        self._configs = configs
        self._catalog = catalog
        self._new_id = new_id

    async def list(self, user_id: UUID) -> list[SubscriptionView]:
        collected = await self._collected_pair_ids()
        return [SubscriptionView(s, s.provider_pair_id in collected)
                for s in await self._subscriptions.list_for_user(user_id)]

    async def create(self, user_id: UUID, new: NewSubscription) -> SubscriptionView:
        pair = await self._catalog.get_pair_by_id(new.provider_pair_id)
        if pair is None:
            raise InvalidSubscriptionError(f"no rate {new.provider_pair_id}")
        if new.provider_pair_id not in await self._collected_pair_ids():
            raise InvalidSubscriptionError(
                f"{pair.provider} {pair.label} isn't being collected, so it can't be emailed")
        if await self._subscriptions.exists_for(user_id, pair.id):
            raise ConflictError(f"already subscribed to {pair.provider} {pair.label}",
                                code="already_subscribed")
        subscription = Subscription(
            id=self._new_id(), user_id=user_id, provider_pair_id=pair.id, hour=new.hour,
            timezone=new.timezone, is_active=new.is_active, provider=pair.provider,
            base=pair.base, quote=pair.quote)
        await self._subscriptions.add(subscription)
        return SubscriptionView(subscription, collecting=True)

    async def update(self, user_id: UUID, id: UUID,
                     changes: SubscriptionChanges) -> SubscriptionView:
        subscription = await self._owned(user_id, id)
        updated = replace(
            subscription,
            hour=subscription.hour if changes.hour is None else changes.hour,
            timezone=changes.timezone or subscription.timezone,
            is_active=subscription.is_active if changes.is_active is None
            else changes.is_active)
        await self._subscriptions.update(updated)
        return SubscriptionView(updated,
                                updated.provider_pair_id in await self._collected_pair_ids())

    async def delete(self, user_id: UUID, id: UUID) -> None:
        await self._owned(user_id, id)
        await self._subscriptions.delete(id)

    async def _owned(self, user_id: UUID, id: UUID) -> Subscription:
        subscription = await self._subscriptions.get(id)
        if subscription is None or subscription.user_id != user_id:
            raise NotFoundError(f"No subscription {id}")
        return subscription

    async def _collected_pair_ids(self) -> set[UUID]:
        pairs = {(p.provider_id, p.base, p.quote): p.id for p in await self._catalog.pairs()}
        return {pairs[key] for c in await self._configs.list_active(IntervalKind.DAILY)
                if (key := (c.provider_id, c.base, c.quote)) in pairs}
