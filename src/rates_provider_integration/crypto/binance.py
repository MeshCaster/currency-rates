import json
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import httpx
from pydantic import TypeAdapter

from domain.enums import IntervalKind
from domain.models import Rate
from rates_provider_integration.models.binance import BinanceTicker
from rates_provider_integration.errors import RateProviderError
from rates_provider_integration.history import require_daily, utc_midnight
from rates_provider_integration.http_clients import default_client

_tickers_adapter = TypeAdapter(list[BinanceTicker])
_klines_adapter = TypeAdapter(list[list[Any]])
_MAX_KLINES = 1000

class BinanceProvider:
    BASE_URL = "https://data-api.binance.vision/api/v3/"
    name = "binance"
    chunk_days = _MAX_KLINES

    def __init__(self, client: httpx.AsyncClient | None = None, *,
                 base_url: str | None = None) -> None:
        self._owns_client = client is None
        self._client = client or default_client()
        self._base_url = base_url or self.BASE_URL

    async def get_rate(self, base: str, quote: str = "USDT") -> Rate:
        base, quote = base.upper(), quote.upper()
        content = await self._get("ticker/price", {"symbol": f"{base}{quote}"})
        ticker = BinanceTicker.model_validate_json(content)
        return self._to_rate(ticker, base, quote)

    async def get_rates(self, pairs: list[tuple[str, str]]) -> list[Rate]:
        by_symbol = {f"{b.upper()}{q.upper()}": (b.upper(), q.upper()) for b, q in pairs}
        symbols = json.dumps(list(by_symbol), separators=(",", ":"))
        content = await self._get("ticker/price", {"symbols": symbols})
        return [self._to_rate(t, *by_symbol[t.symbol]) for t in _tickers_adapter.validate_json(content)]

    async def get_history(self, base: str, quote: str, start: date, end: date,
                          interval: IntervalKind = IntervalKind.DAILY) -> list[Rate]:
        require_daily(self.name, interval)
        base, quote = base.upper(), quote.upper()
        content = await self._get("klines", {
            "symbol": f"{base}{quote}", "interval": "1d",
            "startTime": str(_ms(utc_midnight(start))),
            "endTime": str(_ms(utc_midnight(end + timedelta(days=1))) - 1),
            "limit": str(_MAX_KLINES)})
        return [Rate(base=base, quote=quote, value=Decimal(str(k[4])), source=self.name,
                     as_of=utc_midnight(datetime.fromtimestamp(k[0] / 1000, UTC).date()))
                for k in _klines_adapter.validate_json(content)]

    async def _get(self, path: str, params: dict[str, str]) -> bytes:
        try:
            response = await self._client.get(f"{self._base_url}{path}", params=params)
        except httpx.HTTPError as e:
            raise RateProviderError(f"Binance request failed: {e}") from e

        if response.status_code in (418, 429):
            raise RateProviderError(f"Binance rate limit hit ({response.status_code}); back off")
        if response.status_code in (403, 451):
            raise RateProviderError(f"Binance blocked this region ({response.status_code})")
        if response.is_error:
            try:
                body = response.json()
                message = f"{body.get('code')}: {body.get('msg')}"
            except ValueError:
                message = response.text[:200]
            raise RateProviderError(f"Binance {response.status_code}: {message}")
        return response.content

    def _to_rate(self, ticker: BinanceTicker, base: str, quote: str) -> Rate:
        return Rate(
            base=base,
            quote=quote,
            value=ticker.price,
            source=self.name,
            as_of=datetime.now(timezone.utc),
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "BinanceProvider":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()


def _ms(moment: datetime) -> int:
    return int(moment.timestamp() * 1000)
