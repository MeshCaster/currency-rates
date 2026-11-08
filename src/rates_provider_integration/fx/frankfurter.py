from datetime import date, datetime, time, timezone

import httpx
from pydantic import TypeAdapter

from rates_provider_integration.models.common import Rate, RateProviderError, default_client
from rates_provider_integration.models.frankfurter import FrankfurterRate

_rows_adapter = TypeAdapter(list[FrankfurterRate])

class FrankfurterProvider:
    BASE_URL = "https://api.frankfurter.dev/v2/"
    name = "frankfurter"

    def __init__(self, client: httpx.AsyncClient | None = None, *,
                 providers: str | None = None) -> None:
        self._owns_client = client is None
        self._client = client or default_client()
        self._providers = providers

    async def get_rate(self, base: str, quote: str, on: date | None = None) -> Rate:
        params = self._params(date=on)
        content = await self._get(f"{self.BASE_URL}rate/{base.upper()}/{quote.upper()}", params)
        return self._to_rate(FrankfurterRate.model_validate_json(content))

    async def get_rates(self, base: str = "EUR", quotes: list[str] | None = None,
                        on: date | None = None) -> list[Rate]:
        params = self._params(
            base=base.upper(),
            quotes=",".join(q.upper() for q in quotes) if quotes else None,
            date=on,
        )
        content = await self._get(f"{self.BASE_URL}rates", params)
        return [self._to_rate(row) for row in _rows_adapter.validate_json(content)]

    async def get_history(self, base: str, quote: str, start: date,
                          end: date | None = None) -> list[Rate]:
        params = self._params(base=base.upper(), quotes=quote.upper(), **{"from": start, "to": end})
        content = await self._get(f"{self.BASE_URL}rates", params)
        return [self._to_rate(row) for row in _rows_adapter.validate_json(content)]

    def _params(self, **values: object) -> dict[str, str]:
        params = {k: (v.isoformat() if isinstance(v, date) else str(v))
                  for k, v in values.items() if v is not None}
        if self._providers:
            params["providers"] = self._providers
        return params

    async def _get(self, url: str, params: dict[str, str]) -> bytes:
        try:
            response = await self._client.get(url, params=params)
        except httpx.HTTPError as e:
            raise RateProviderError(f"Frankfurter request failed: {e}") from e

        if response.is_error:
            try:
                message = response.json().get("message", response.text)
            except ValueError:
                message = response.text
            raise RateProviderError(f"Frankfurter {response.status_code}: {message}")
        return response.content

    def _to_rate(self, row: FrankfurterRate) -> Rate:
        return Rate(
            base=row.base,
            quote=row.quote,
            value=row.rate,
            source=f"{self.name}:{self._providers or 'blended'}",
            as_of=datetime.combine(row.date, time.min, tzinfo=timezone.utc),
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "FrankfurterProvider":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()