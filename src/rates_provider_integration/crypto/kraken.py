from datetime import UTC, date, datetime, timezone
from decimal import Decimal

import httpx

from domain.enums import IntervalKind
from domain.models import Rate
from rates_provider_integration.history import require_daily, utc_midnight
from rates_provider_integration.models.kraken import (
    _KRAKEN_ASSETS,
    KrakenOHLCResponse,
    KrakenTicker,
    KrakenTickerResponse,
)

from rates_provider_integration.errors import RateProviderError
from rates_provider_integration.http_clients import default_client

class KrakenProvider:
    BASE_URL = "https://api.kraken.com/0/public/"
    name = "kraken"
    chunk_days = 720

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

    async def get_history(self, base: str, quote: str, start: date, end: date,
                          interval: IntervalKind = IntervalKind.DAILY) -> list[Rate]:
        require_daily(self.name, interval)
        pair = f"{self._asset(base)}{self._asset(quote)}"
        since = int(utc_midnight(start).timestamp()) - 1
        try:
            response = await self._client.get(f"{self.BASE_URL}OHLC", params={
                "pair": pair, "interval": "1440", "since": str(since)})
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise RateProviderError(f"Kraken request failed: {e}") from e

        payload = KrakenOHLCResponse.model_validate_json(response.content)
        if payload.error:
            raise RateProviderError(f"Kraken error: {', '.join(payload.error)}")
        candles = next((v for k, v in payload.result.items() if k != "last"
                        and isinstance(v, list)), [])
        closes = {datetime.fromtimestamp(int(c[0]), UTC).date(): Decimal(str(c[4]))
                  for c in candles}
        first = min(closes, default=None)
        if first is not None and first > start:
            raise RateProviderError(
                f"Kraken keeps daily {pair} candles from {first} only; asked from {start}")
        return [Rate(base=base.upper(), quote=quote.upper(), value=close, source=self.name,
                     as_of=utc_midnight(day))
                for day, close in sorted(closes.items()) if start <= day <= end]

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