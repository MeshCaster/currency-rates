from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from application import SubscriptionService, SyncConfigurationQueryService
from core.dependencies import require_scopes
from host.api.deps import (
    CurrentUserDep,
    get_subscription_service,
    get_sync_configuration_query_service,
)
from host.api.schemas import FeedOut, SubscriptionIn, SubscriptionOut, SubscriptionPatch

router = APIRouter()

SubscriptionsDep = Annotated[SubscriptionService, Depends(get_subscription_service)]
can_read = [Depends(require_scopes("subscriptions:read"))]
can_write = [Depends(require_scopes("subscriptions:write"))]


@router.get("/feeds", response_model=list[FeedOut], tags=["feeds"])
async def list_feeds(
        query: Annotated[SyncConfigurationQueryService,
                         Depends(get_sync_configuration_query_service)],
        page: Annotated[int, Query(ge=1)] = 1,
        size: Annotated[int, Query(ge=1, le=200)] = 200) -> list[FeedOut]:
    found = await query.list(is_active=True, page=page, size=size)
    return [FeedOut.of(v.config) for v in found.items]


@router.get("/me/subscriptions", response_model=list[SubscriptionOut],
            tags=["subscriptions"], dependencies=can_read)
async def list_subscriptions(user: CurrentUserDep,
                             subscriptions: SubscriptionsDep) -> list[SubscriptionOut]:
    return [SubscriptionOut.of(s) for s in await subscriptions.list(user.id)]


@router.post("/me/subscriptions", response_model=SubscriptionOut,
             status_code=status.HTTP_201_CREATED, tags=["subscriptions"], dependencies=can_write)
async def subscribe(body: SubscriptionIn, user: CurrentUserDep,
                    subscriptions: SubscriptionsDep) -> SubscriptionOut:
    return SubscriptionOut.of(await subscriptions.create(user.id, body.to_command()))


@router.patch("/me/subscriptions/{id}", response_model=SubscriptionOut,
              tags=["subscriptions"], dependencies=can_write)
async def update_subscription(id: UUID, body: SubscriptionPatch, user: CurrentUserDep,
                              subscriptions: SubscriptionsDep) -> SubscriptionOut:
    return SubscriptionOut.of(await subscriptions.update(user.id, id, body.to_changes()))


@router.delete("/me/subscriptions/{id}", status_code=status.HTTP_204_NO_CONTENT,
               tags=["subscriptions"], dependencies=can_write)
async def unsubscribe(id: UUID, user: CurrentUserDep, subscriptions: SubscriptionsDep) -> None:
    await subscriptions.delete(user.id, id)
