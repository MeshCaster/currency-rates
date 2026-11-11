from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status

from application import SyncConfigurationAdminService, SyncConfigurationQueryService
from core.dependencies import require_scopes
from core.exceptions.not_found_error import NotFoundError
from host.api.deps import get_sync_configuration_admin_service, get_sync_configuration_query_service
from host.api.schemas import SyncConfigurationIn, SyncConfigurationOut, SyncConfigurationPageOut

router = APIRouter(prefix="/sync-configurations", tags=["sync configurations"])

QueryDep = Annotated[SyncConfigurationQueryService,
                     Depends(get_sync_configuration_query_service)]
AdminDep = Annotated[SyncConfigurationAdminService,
                     Depends(get_sync_configuration_admin_service)]
can_read = [Depends(require_scopes("sync:read"))]
can_write = [Depends(require_scopes("sync:write"))]


@router.get("", response_model=SyncConfigurationPageOut, dependencies=can_read)
async def list_sync_configurations(
        query: QueryDep,
        provider: Annotated[str | None, Query(description="Provider key, e.g. nbg")] = None,
        is_active: bool | None = None,
        page: Annotated[int, Query(ge=1)] = 1,
        size: Annotated[int, Query(ge=1, le=200)] = 50) -> SyncConfigurationPageOut:
    found = await query.list(provider=provider, is_active=is_active, page=page, size=size)
    return SyncConfigurationPageOut(items=[SyncConfigurationOut.of(v) for v in found.items],
                                    total=found.total, page=found.page, size=found.size)


@router.get("/{id}", response_model=SyncConfigurationOut, dependencies=can_read)
async def get_sync_configuration(id: UUID, query: QueryDep) -> SyncConfigurationOut:
    view = await query.get(id)
    if view is None:
        raise NotFoundError(f"No sync configuration {id}")
    return SyncConfigurationOut.of(view)


@router.post("", response_model=SyncConfigurationOut, status_code=status.HTTP_201_CREATED,
             dependencies=can_write)
async def create_sync_configuration(body: SyncConfigurationIn, admin: AdminDep,
                                    request: Request, response: Response) -> SyncConfigurationOut:
    view = await admin.create(body.to_command())
    response.headers["Location"] = str(request.url_for("get_sync_configuration",
                                                       id=view.config.id))
    return SyncConfigurationOut.of(view)
