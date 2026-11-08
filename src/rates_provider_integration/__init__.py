from rates_provider_integration.models.common import Rate, RateProvider, RateProviderError, default_client

from .fx.er import ERApiProvider
from .fx.frankfurter import FrankfurterProvider
from .fx.nbg import NBGProvider

from .crypto.kraken import KrakenProvider
from .crypto.coin_gecko import CoinGeckoProvider
from .crypto.binance import BinanceProvider
from .crypto.coinbase import CoinbaseProvider

__all__ = [
    "Rate",
    "RateProvider",
    "RateProviderError",
    "default_client",
    "ERApiProvider",
    "FrankfurterProvider",
    "NBGProvider",
    "BinanceProvider",
    "CoinbaseProvider",
    "CoinGeckoProvider",
    "KrakenProvider",
]