from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status

from application import SyncConfigurationAdminService, SyncConfigurationQueryService
from core.dependencies import PaginationDep, require_scopes
from core.exceptions.not_found_error import NotFoundError
from core.pagination import PageResponse
from host.api.deps import get_sync_configuration_admin_service, get_sync_configuration_query_service
from host.api.schemas import SyncConfigurationIn, SyncConfigurationOut

router = APIRouter(prefix="/sync-configurations", tags=["sync configurations"])

QueryDep = Annotated[SyncConfigurationQueryService,
                     Depends(get_sync_configuration_query_service)]
AdminDep = Annotated[SyncConfigurationAdminService,
                     Depends(get_sync_configuration_admin_service)]
can_read = [Depends(require_scopes("sync:read"))]
can_write = [Depends(require_scopes("sync:write"))]


@router.get("", response_model=PageResponse[SyncConfigurationOut], dependencies=can_read)
async def list_sync_configurations(
        query: QueryDep, paging: PaginationDep,
        provider: Annotated[str | None, Query(description="Provider key, e.g. nbg")] = None,
        is_active: bool | None = None) -> PageResponse[SyncConfigurationOut]:
    found = await query.list(provider=provider, is_active=is_active, page=paging.page,
                             size=paging.size)
    return PageResponse[SyncConfigurationOut].of(found, SyncConfigurationOut.of)


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
