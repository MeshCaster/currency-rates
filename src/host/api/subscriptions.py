from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from application import FeedQueryService, SubscriptionService
from core.dependencies import require_scopes
from core.exceptions.not_found_error import NotFoundError
from host.api.deps import (
    CurrentUserDep,
    get_feed_query_service,
    get_subscription_service,
)
from host.api.schemas import (
    FeedPointOut,
    FeedRateOut,
    SubscriptionIn,
    SubscriptionOut,
    SubscriptionPatch,
)

router = APIRouter()

SubscriptionsDep = Annotated[SubscriptionService, Depends(get_subscription_service)]
can_read = [Depends(require_scopes("subscriptions:read"))]
can_write = [Depends(require_scopes("subscriptions:write"))]


FeedsDep = Annotated[FeedQueryService, Depends(get_feed_query_service)]


@router.get("/feeds", response_model=list[FeedRateOut], tags=["feeds"])
async def list_feeds(feeds: FeedsDep) -> list[FeedRateOut]:
    return [FeedRateOut.of_view(v) for v in await feeds.all()]


@router.get("/feeds/{id}", response_model=FeedRateOut, tags=["feeds"])
async def get_feed(id: UUID, feeds: FeedsDep) -> FeedRateOut:
    view = await feeds.get(id)
    if view is None:
        raise NotFoundError(f"No feed {id}")
    return FeedRateOut.of_view(view)


@router.get("/feeds/{id}/history", response_model=list[FeedPointOut], tags=["feeds"])
async def feed_history(id: UUID, feeds: FeedsDep,
                       days: Annotated[int, Query(ge=1, le=730)] = 30) -> list[FeedPointOut]:
    rates = await feeds.history(id, days)
    if rates is None:
        raise NotFoundError(f"No feed {id}")
    return [FeedPointOut(day=r.as_of.date(), value=r.value) for r in rates]


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
