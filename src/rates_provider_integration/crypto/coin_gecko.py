import time as _time
from datetime import datetime, timezone
from decimal import Decimal

import httpx
from pydantic import TypeAdapter

from domain.models import Rate
from rates_provider_integration.models.coin_gecko import DEFAULT_COIN_IDS
from rates_provider_integration.errors import RateProviderError
from rates_provider_integration.http_clients import default_client

_price_adapter = TypeAdapter(dict[str, dict[str, Decimal]])

class CoinGeckoProvider:
    BASE_URL = "https://api.coingecko.com/api/v3/"
    name = "coingecko"

    def __init__(self, client: httpx.AsyncClient | None = None, *,
                 api_key: str | None = None,
                 coin_ids: dict[str, str] | None = None,
                 cache_seconds: float = 60.0) -> None:
        self._owns_client = client is None
        self._client = client or default_client()
        self._headers = {"x-cg-demo-api-key": api_key} if api_key else {}
        self._coin_ids = {**DEFAULT_COIN_IDS, **(coin_ids or {})}
        self._cache_seconds = cache_seconds
        self._cache: dict[tuple[str, str], tuple[float, Rate]] = {}

    async def get_rate(self, base: str, quote: str = "USD") -> Rate:
        return (await self.get_rates([base], [quote]))[0]

    async def get_rates(self, bases: list[str], quotes: list[str]) -> list[Rate]:
        bases = [b.upper() for b in bases]
        quotes = [q.upper() for q in quotes]
        wanted = [(b, q) for b in bases for q in quotes]

        now = _time.monotonic()
        cached = {k: v for k, v in self._cache.items() if now - v[0] < self._cache_seconds}
        missing = [(b, q) for b, q in wanted if (self._coin_id(b), q.lower()) not in cached]

        if missing:
            await self._fetch({b for b, _ in missing}, {q for _, q in missing})

        return [self._cache[(self._coin_id(b), q.lower())][1] for b, q in wanted]

    async def _fetch(self, bases: set[str], quotes: set[str]) -> None:
        ids = {self._coin_id(b): b for b in bases}
        params = {
            "ids": ",".join(ids),
            "vs_currencies": ",".join(q.lower() for q in quotes),
            "include_last_updated_at": "true",
            "precision": "full",
        }
        try:
            response = await self._client.get(f"{self.BASE_URL}simple/price",
                                              params=params, headers=self._headers)
        except httpx.HTTPError as e:
            raise RateProviderError(f"CoinGecko request failed: {e}") from e

        if response.status_code == 429:
            raise RateProviderError("CoinGecko rate limit hit (429); back off or use a Demo key")
        if response.is_error:
            raise RateProviderError(f"CoinGecko {response.status_code}: {response.text[:200]}")

        payload = _price_adapter.validate_json(response.content)
        fetched_at = _time.monotonic()

        for coin_id, symbol in ids.items():
            prices = payload.get(coin_id)
            if not prices:
                raise RateProviderError(f"CoinGecko has no price for {symbol!r} (id {coin_id!r})")
            updated = prices.get("last_updated_at")
            as_of = (datetime.fromtimestamp(int(updated), tz=timezone.utc) if updated
                     else datetime.now(timezone.utc))
            for quote in quotes:
                value = prices.get(quote.lower())
                if value is None:
                    raise RateProviderError(f"CoinGecko has no {symbol}/{quote} price")
                self._cache[(coin_id, quote.lower())] = (
                    fetched_at,
                    Rate(base=symbol, quote=quote, value=value, source=self.name, as_of=as_of),
                )

    def _coin_id(self, symbol: str) -> str:
        try:
            return self._coin_ids[symbol.upper()]
        except KeyError:
            raise RateProviderError(
                f"No CoinGecko ID known for {symbol!r}; pass coin_ids={{'{symbol.upper()}': '<id>'}}"
            ) from None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "CoinGeckoProvider":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()