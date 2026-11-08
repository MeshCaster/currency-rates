from datetime import date, datetime
from decimal import Decimal

import httpx
from pydantic import TypeAdapter

from domain.models import Rate
from rates_provider_integration.errors import RateProviderError
from rates_provider_integration.http_clients import default_client
from rates_provider_integration.models.nbg import GEL, NBGRatesResponse, NBGRate

_response_adapter = TypeAdapter(list[NBGRatesResponse])

class NBGProvider:
    BASE_URL = "https://nbg.gov.ge/gw/api/ct/monetarypolicy/currencies/en/json/"
    name = "nbg"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._owns_client = client is None
        self._client = client or default_client()
        self._cache: dict[str, NBGRatesResponse] = {}

    async def get_rates(self, on: date | None = None) -> list[NBGRate]:
        return (await self._fetch(on)).rates

    async def get_rate(self, base: str, quote: str, on: date | None = None) -> Rate:
        base, quote = base.upper(), quote.upper()
        if base == quote:
            raise RateProviderError("Base and quote must differ")

        table = await self._fetch(on)
        by_code = {r.code: r for r in table.rates}

        def gel_per_unit(code: str) -> Decimal:
            if code == GEL:
                return Decimal(1)
            try:
                return by_code[code].rate_per_unit
            except KeyError:
                raise RateProviderError(f"Currency {code!r} not in NBG rates") from None

        value = gel_per_unit(base) / gel_per_unit(quote)
        return Rate(base=base, quote=quote, value=value, source=self.name, as_of=table.date)

    async def _fetch(self, on: date | None) -> NBGRatesResponse:
        key = on.isoformat() if on else "latest"
        cached = self._cache.get(key)
        if cached and (on is not None or self._is_current(cached)):
            return cached

        params = {"date": on.isoformat()} if on else None
        try:
            response = await self._client.get(self.BASE_URL, params=params)
            response.raise_for_status()
        except httpx.HTTPError as e:
            if cached:
                return cached
            raise RateProviderError(f"NBG request failed: {e}") from e

        payload = _response_adapter.validate_json(response.content)
        if not payload or not payload[0].rates:
            raise RateProviderError("NBG returned an empty response")

        self._cache[key] = payload[0]
        return payload[0]

    @staticmethod
    def _is_current(table: NBGRatesResponse) -> bool:
        today = datetime.now(table.date.tzinfo).date()
        return table.date.date() >= today

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "NBGProvider":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()