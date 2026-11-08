from datetime import date, datetime, time, timezone

import httpx

from ..models.coinbase import PriceKind, CoinbasePriceResponse
from ..models.common import Rate, RateProviderError, default_client


class CoinbaseProvider:
    BASE_URL = "https://api.coinbase.com/v2/prices/"
    name = "coinbase"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._owns_client = client is None
        self._client = client or default_client()

    async def get_rate(self, base: str, quote: str = "USD", on: date | None = None,
                       kind: PriceKind = "spot") -> Rate:
        if on and kind != "spot":
            raise RateProviderError("Historic prices are only available for kind='spot'")

        base, quote = base.upper(), quote.upper()
        url = f"{self.BASE_URL}{base}-{quote}/{kind}"
        params = {"date": on.isoformat()} if on else None

        try:
            response = await self._client.get(url, params=params)
        except httpx.HTTPError as e:
            raise RateProviderError(f"Coinbase request failed: {e}") from e

        if response.is_error:
            try:
                errors = response.json().get("errors", [])
                message = "; ".join(e.get("message", str(e)) for e in errors) or response.text[:200]
            except ValueError:
                message = response.text[:200]
            raise RateProviderError(f"Coinbase {response.status_code}: {message}")

        price = CoinbasePriceResponse.model_validate_json(response.content).data
        as_of = (datetime.combine(on, time.min, tzinfo=timezone.utc) if on
                 else datetime.now(timezone.utc))
        return Rate(base=base, quote=price.currency, value=price.amount,
                    source=f"{self.name}:{kind}", as_of=as_of)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "CoinbaseProvider":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()