from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from application.ports import RateProvider, RateRepository
from application import HistoricalRateSyncService, RateQueryService, RateSyncService
from infrastructure.db.repositories.rate_repository import SqlRateRepository


async def get_session(request: Request):
    async with request.app.state.session_factory() as session:
        yield session


def get_repository(session: AsyncSession = Depends(get_session)) -> RateRepository:
    return SqlRateRepository(session)


def get_provider(request: Request) -> RateProvider:
    return request.app.state.provider


def get_query_service(repository: RateRepository = Depends(get_repository)) -> RateQueryService:
    return RateQueryService(repository)


def get_sync_service(repository: RateRepository = Depends(get_repository),
                     provider: RateProvider = Depends(get_provider)) -> RateSyncService:
    return RateSyncService(provider, repository)


def get_historical_sync_service(request: Request,
                                repository: RateRepository = Depends(get_repository)) -> HistoricalRateSyncService:
    return HistoricalRateSyncService(request.app.state.provider, repository)
