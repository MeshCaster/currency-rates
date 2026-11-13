from typing import Annotated

from fastapi import APIRouter, Depends

from application import CurrencyQueryService
from core.dependencies import SettingsDep
from host.api.deps import get_currency_query_service
from host.api.schemas import CurrencyOut

router = APIRouter(prefix="/currencies", tags=["currencies"])

CurrenciesDep = Annotated[CurrencyQueryService, Depends(get_currency_query_service)]


@router.get("", response_model=list[CurrencyOut])
async def list_currencies(currencies: CurrenciesDep, settings: SettingsDep) -> list[CurrencyOut]:
    return [CurrencyOut.of(c, settings.storage.url(c.icon)) for c in await currencies.all()]
