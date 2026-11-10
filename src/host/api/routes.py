from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from application import RateQueryService, RateSyncService, HistoricalRateSyncService
from host.api.deps import (
    get_historical_sync_service,
    get_query_service,
    get_session,
    get_sync_service,
)
from host.api.schemas import RateHistoryOut, RateOut, SyncResultOut
from rates_provider_integration.errors import RateProviderError

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/pairs")
async def list_pairs(query: RateQueryService = Depends(get_query_service)):
    return [{"base": b, "quote": q} for b, q in await query.list_pairs()]


@router.get("/rates/{base}/{quote}", response_model=RateOut)
async def latest_rate(base: str, quote: str, query: RateQueryService = Depends(get_query_service)):
    rate = await query.latest(base, quote)
    if rate is None:
        raise HTTPException(status_code=404, detail=f"No rate for {base.upper()}/{quote.upper()}")
    return rate


@router.get("/rates/{base}/{quote}/history", response_model=RateHistoryOut)
async def history(base: str, quote: str, query: RateQueryService = Depends(get_query_service),
                  page: int = Query(1, ge=1), size: int = Query(50, ge=1, le=1000)):
    result = await query.history(base, quote, page=page, size=size)
    return RateHistoryOut(items=[RateOut.model_validate(r) for r in result.items],
                          total=result.total, page=result.page, size=result.size)


@router.post("/rates/{base}/{quote}/sync", response_model=RateOut)
async def sync_now(base: str, quote: str, service: RateSyncService = Depends(get_sync_service),
                   session: AsyncSession = Depends(get_session)):
    try:
        rate = await service.sync(base, quote)
    except RateProviderError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    await session.commit()
    return rate


@router.post("/rates/{base}/{quote}/backfill", response_model=SyncResultOut)
async def backfill(base: str, quote: str, since: date, until: date,
                   service: HistoricalRateSyncService = Depends(get_historical_sync_service),
                   session: AsyncSession = Depends(get_session)):
    if since > until:
        raise HTTPException(status_code=422, detail="since must be on or before until")
    if (until - since).days > 366:
        raise HTTPException(status_code=422, detail="range must span at most 366 days")
    result = await service.sync_range(base, quote, since, until)
    await session.commit()
    return SyncResultOut.model_validate(result)
