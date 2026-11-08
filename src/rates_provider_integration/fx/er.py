from datetime import datetime, timezone

import httpx

from rates_provider_integration.models.common import Rate, RateProviderError, default_client
from rates_provider_integration.models.er import ERRatesResponse


class ERApiProvider:
    BASE_URL = "https://open.er-api.com/v6/latest/"
    name = "exchangerate-api"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._owns_client = client is None
        self._client = client or default_client()
        self._cache: dict[str, ERRatesResponse] = {}

    async def get_rates(self, base: str = "USD") -> ERRatesResponse:
        base = base.upper()
        cached = self._cache.get(base)
        if cached and datetime.now(timezone.utc) < cached.next_update:
            return cached

        try:
            response = await self._client.get(f"{self.BASE_URL}{base}")
        except httpx.HTTPError as e:
            raise RateProviderError(f"ExchangeRate-API request failed: {e}") from e

        if response.status_code == 429:
            if cached:
                return cached
            raise RateProviderError("ExchangeRate-API rate limit hit (429); retry in ~20 minutes")
        if response.is_error:
            raise RateProviderError(f"ExchangeRate-API {response.status_code}: {response.text[:200]}")

        payload = ERRatesResponse.model_validate_json(response.content)
        if payload.result != "success":
            raise RateProviderError(f"ExchangeRate-API error: {payload.error_type or 'unknown'}")

        self._cache[base] = payload
        return payload

    async def get_rate(self, base: str, quote: str) -> Rate:
        payload = await self.get_rates(base)
        quote = quote.upper()
        try:
            value = payload.rates[quote]
        except KeyError:
            raise RateProviderError(f"Currency {quote!r} not available from ExchangeRate-API") from None
        return Rate(
            base=payload.base_code or base.upper(),
            quote=quote,
            value=value,
            source=self.name,
            as_of=payload.last_update,
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "ERApiProvider":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()