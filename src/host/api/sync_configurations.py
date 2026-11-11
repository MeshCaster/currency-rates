from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from application import SyncConfigurationQueryService
from core.dependencies import require_scopes
from core.exceptions.not_found_error import NotFoundError
from host.api.deps import get_sync_configuration_query_service
from host.api.schemas import SyncConfigurationOut, SyncConfigurationPageOut

router = APIRouter(prefix="/sync-configurations", tags=["sync configurations"],
                   dependencies=[Depends(require_scopes("sync:read"))])

QueryDep = Annotated[SyncConfigurationQueryService,
                     Depends(get_sync_configuration_query_service)]


@router.get("", response_model=SyncConfigurationPageOut)
async def list_sync_configurations(
        query: QueryDep,
        provider: Annotated[str | None, Query(description="Provider key, e.g. nbg")] = None,
        is_active: bool | None = None,
        page: Annotated[int, Query(ge=1)] = 1,
        size: Annotated[int, Query(ge=1, le=200)] = 50) -> SyncConfigurationPageOut:
    found = await query.list(provider=provider, is_active=is_active, page=page, size=size)
    return SyncConfigurationPageOut(items=[SyncConfigurationOut.of(v) for v in found.items],
                                    total=found.total, page=found.page, size=found.size)


@router.get("/{id}", response_model=SyncConfigurationOut)
async def get_sync_configuration(id: UUID, query: QueryDep) -> SyncConfigurationOut:
    view = await query.get(id)
    if view is None:
        raise NotFoundError(f"No sync configuration {id}")
    return SyncConfigurationOut.of(view)
