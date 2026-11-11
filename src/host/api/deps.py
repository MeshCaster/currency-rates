from fastapi import Depends, Request

from application.ports import RateProvider, RateRepository
from application import (HistoricalRateSyncService, RateQueryService,
                         SyncConfigurationQueryService)
from core.dependencies import DbSessionDep
from infrastructure.db.repositories.rate_repository import SqlRateRepository
from infrastructure.db.repositories.sync_configuration_repository import (
    SqlSyncConfigurationRepository,
)


def get_repository(session: DbSessionDep) -> RateRepository:
    return SqlRateRepository(session)


def get_provider(request: Request) -> RateProvider:
    return request.state.provider


def get_query_service(repository: RateRepository = Depends(get_repository)) -> RateQueryService:
    return RateQueryService(repository)


def get_historical_sync_service(repository: RateRepository = Depends(get_repository),
                                provider: RateProvider = Depends(get_provider)) -> HistoricalRateSyncService:
    return HistoricalRateSyncService(provider, repository)


def get_sync_configuration_query_service(session: DbSessionDep) -> SyncConfigurationQueryService:
    return SyncConfigurationQueryService(SqlSyncConfigurationRepository(session))
