from collections.abc import Mapping
from typing import Any

import httpx

from application.ports import RateHistoryProvider, RateProvider
from domain.errors import UnsupportedSyncError
from rates_provider_integration.crypto.coinbase import CoinbaseProvider
from rates_provider_integration.fx.frankfurter import FrankfurterProvider
from rates_provider_integration.fx.nbg import NBGProvider
from rates_provider_integration.history import DailyHistory


def default_provider(http_client: httpx.AsyncClient) -> RateProvider:
    return NBGProvider(http_client)


class HistoryProviders:
    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._http = http_client

    def __call__(self, key: str, options: Mapping[str, Any] | None = None) -> RateHistoryProvider:
        options = options or {}
        match key:
            case "frankfurter":
                return FrankfurterProvider(self._http, providers=options.get("providers"))
            case "nbg":
                return DailyHistory(NBGProvider(self._http))
            case "coinbase":
                return DailyHistory(CoinbaseProvider(self._http))
            case _:
                raise UnsupportedSyncError(f"provider {key!r} has no history integration yet")
