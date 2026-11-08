from datetime import datetime, timezone

import httpx

from ..models.kraken import _KRAKEN_ASSETS, KrakenTickerResponse, KrakenTicker

from ..models.common import Rate, RateProviderError, default_client

class KrakenProvider:
    BASE_URL = "https://api.kraken.com/0/public/"
    name = "kraken"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._owns_client = client is None
        self._client = client or default_client()

    async def get_ticker(self, base: str, quote: str = "USD") -> KrakenTicker:
        pair = f"{self._asset(base)}{self._asset(quote)}"
        try:
            response = await self._client.get(f"{self.BASE_URL}Ticker", params={"pair": pair})
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise RateProviderError(f"Kraken request failed: {e}") from e

        payload = KrakenTickerResponse.model_validate_json(response.content)
        if payload.error:
            raise RateProviderError(f"Kraken error: {', '.join(payload.error)}")
        if not payload.result:
            raise RateProviderError(f"Kraken returned no ticker for {pair}")
        return next(iter(payload.result.values()))

    async def get_rate(self, base: str, quote: str = "USD") -> Rate:
        ticker = await self.get_ticker(base, quote)
        return Rate(
            base=base.upper(),
            quote=quote.upper(),
            value=ticker.last,
            source=self.name,
            as_of=datetime.now(timezone.utc),
        )

    @staticmethod
    def _asset(code: str) -> str:
        code = code.upper()
        return _KRAKEN_ASSETS.get(code, code)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "KrakenProvider":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()