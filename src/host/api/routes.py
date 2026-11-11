from datetime import date

from fastapi import APIRouter, Depends, Query

from application import HistoricalRateSyncService, RateQueryService
from core.exceptions.bad_request_error import BadRequestError
from core.exceptions.not_found_error import NotFoundError
from host.api.deps import get_historical_sync_service, get_query_service
from host.api.schemas import RateHistoryOut, RateOut, SyncResultOut

router = APIRouter(tags=["rates"])


@router.get("/pairs")
async def list_pairs(query: RateQueryService = Depends(get_query_service)):
    return [{"base": b, "quote": q} for b, q in await query.list_pairs()]


@router.get("/rates/{base}/{quote}", response_model=RateOut)
async def latest_rate(base: str, quote: str, query: RateQueryService = Depends(get_query_service)):
    rate = await query.latest(base, quote)
    if rate is None:
        raise NotFoundError(f"No rate for {base.upper()}/{quote.upper()}")
    return rate


@router.get("/rates/{base}/{quote}/history", response_model=RateHistoryOut)
async def history(base: str, quote: str, query: RateQueryService = Depends(get_query_service),
                  page: int = Query(1, ge=1), size: int = Query(50, ge=1, le=1000)):
    result = await query.history(base, quote, page=page, size=size)
    return RateHistoryOut(items=[RateOut.model_validate(r) for r in result.items],
                          total=result.total, page=result.page, size=result.size)


@router.post("/rates/{base}/{quote}/backfill", response_model=SyncResultOut)
async def backfill(base: str, quote: str, since: date, until: date,
                   service: HistoricalRateSyncService = Depends(get_historical_sync_service)):
    if since > until:
        raise BadRequestError("since must be on or before until")
    if (until - since).days > 366:
        raise BadRequestError("range must span at most 366 days")
    result = await service.sync_range(base, quote, since, until)
    return SyncResultOut.model_validate(result)
