from collections.abc import Callable, Mapping
from typing import Any

import httpx

from application.ports import RateHistoryProvider, RateProvider
from domain.errors import UnsupportedSyncError
from rates_provider_integration.crypto.binance import BinanceProvider
from rates_provider_integration.crypto.coin_gecko import CoinGeckoProvider
from rates_provider_integration.crypto.coinbase import CoinbaseProvider
from rates_provider_integration.crypto.kraken import KrakenProvider
from rates_provider_integration.fx.frankfurter import FrankfurterProvider
from rates_provider_integration.fx.nbg import NBGProvider
from rates_provider_integration.history import DailyHistory


def default_provider(http_client: httpx.AsyncClient) -> RateProvider:
    return NBGProvider(http_client)


type HistoryBuilder = Callable[[httpx.AsyncClient, Mapping[str, Any]], RateHistoryProvider]

_REGISTRY: dict[str, HistoryBuilder] = {
    "frankfurter": lambda http, options: FrankfurterProvider(
        http, providers=options.get("providers")),
    "nbg": lambda http, options: DailyHistory(NBGProvider(http)),
    "coinbase": lambda http, options: DailyHistory(CoinbaseProvider(http)),
    "binance": lambda http, options: BinanceProvider(http),
    "kraken": lambda http, options: KrakenProvider(http),
    "coingecko": lambda http, options: CoinGeckoProvider(http),
}


class HistoryProviders:
    KEYS = frozenset(_REGISTRY)

    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._http = http_client

    def __call__(self, key: str, options: Mapping[str, Any] | None = None) -> RateHistoryProvider:
        builder = _REGISTRY.get(key)
        if builder is None:
            raise UnsupportedSyncError(f"provider {key!r} has no history integration yet")
        return builder(self._http, options or {})
