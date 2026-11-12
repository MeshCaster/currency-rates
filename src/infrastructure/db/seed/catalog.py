from datetime import date

from domain.enums import CurrencyKind, IntervalKind, ProviderKind
from domain.models import IntervalCapability
from infrastructure.db.seed.models import CurrencySeed, ProviderSeed, SyncSeed

DAILY, MONTHLY = IntervalKind.DAILY, IntervalKind.MONTHLY

CURRENCIES: tuple[CurrencySeed, ...] = (
    CurrencySeed("USD", "US Dollar", CurrencyKind.FIAT),
    CurrencySeed("EUR", "Euro", CurrencyKind.FIAT),
    CurrencySeed("GBP", "Pound Sterling", CurrencyKind.FIAT),
    CurrencySeed("GEL", "Georgian Lari", CurrencyKind.FIAT),
    CurrencySeed("BTC", "Bitcoin", CurrencyKind.CRYPTO),
    CurrencySeed("ETH", "Ether", CurrencyKind.CRYPTO),
    CurrencySeed("USDT", "Tether", CurrencyKind.STABLECOIN),
)

PROVIDERS: tuple[ProviderSeed, ...] = (
    ProviderSeed(
        "frankfurter", "Frankfurter", ProviderKind.FX,
        intervals=(
            IntervalCapability(DAILY, is_native=True, history_start=date(1999, 1, 4)),
            IntervalCapability(MONTHLY, is_native=True, history_start=date(1999, 1, 4)),
        ),
        currencies=("USD", "EUR", "GBP", "GEL"),
        dev_sync=(
            SyncSeed("EUR", "USD", DAILY, days_back=730, options={"providers": "ECB"}),
            SyncSeed("USD", "GEL", DAILY, days_back=365),
            SyncSeed("EUR", "USD", MONTHLY, days_back=730, options={"providers": "ECB"},
                     is_active=False),
        ),
    ),
    ProviderSeed(
        "nbg", "National Bank of Georgia", ProviderKind.FX,
        intervals=(
            IntervalCapability(DAILY, is_native=True, history_start=date(1996, 1, 6),
                         max_points_per_request=1),
            IntervalCapability(MONTHLY, is_native=False, history_start=date(1996, 1, 6),
                         max_points_per_request=1),
        ),
        currencies=("USD", "EUR", "GBP", "GEL"),
        dev_sync=(
            SyncSeed("USD", "GEL", DAILY, days_back=30),
            SyncSeed("EUR", "GEL", DAILY, days_back=30),
            SyncSeed("GBP", "GEL", DAILY, days_back=30),
            SyncSeed("USD", "GEL", MONTHLY, days_back=365, is_active=False),
        ),
    ),
    ProviderSeed(
        "exchangerate-api", "ExchangeRate-API", ProviderKind.FX, requires_api_key=True,
    ),
    ProviderSeed(
        "binance", "Binance", ProviderKind.CRYPTO,
        intervals=(
            IntervalCapability(DAILY, is_native=True, max_points_per_request=1000),
            IntervalCapability(MONTHLY, is_native=True, max_points_per_request=1000),
        ),
        currencies=("BTC", "ETH", "USDT"),
        dev_sync=(
            SyncSeed("BTC", "USDT", DAILY, days_back=365),
            SyncSeed("ETH", "USDT", DAILY, days_back=365),
            SyncSeed("BTC", "USDT", MONTHLY, days_back=730, is_active=False),
        ),
    ),
    ProviderSeed(
        "coinbase", "Coinbase", ProviderKind.CRYPTO,
        intervals=(
            IntervalCapability(DAILY, is_native=True, history_start=date(2023, 10, 1),
                         max_points_per_request=1),
            IntervalCapability(MONTHLY, is_native=False, history_start=date(2023, 10, 1),
                         max_points_per_request=1),
        ),
        currencies=("BTC", "ETH", "USD", "EUR"),
        dev_sync=(
            SyncSeed("BTC", "USD", DAILY, days_back=14),
            SyncSeed("ETH", "USD", DAILY, days_back=14),
            SyncSeed("BTC", "USD", MONTHLY, days_back=365, is_active=False),
        ),
    ),
    ProviderSeed(
        "kraken", "Kraken", ProviderKind.CRYPTO,
        intervals=(
            IntervalCapability(DAILY, is_native=True, history_window_days=720,
                         max_points_per_request=720),
            IntervalCapability(MONTHLY, is_native=False, history_window_days=720,
                         max_points_per_request=720),
        ),
        currencies=("BTC", "ETH", "USD", "EUR"),
        provider_codes={"BTC": "XBT"},
        dev_sync=(
            SyncSeed("BTC", "USD", DAILY, days_back=365),
            SyncSeed("BTC", "USD", MONTHLY, days_back=600, is_active=False),
        ),
    ),
    ProviderSeed(
        "coingecko", "CoinGecko", ProviderKind.CRYPTO,
        intervals=(
            IntervalCapability(DAILY, is_native=True, history_window_days=365),
            IntervalCapability(MONTHLY, is_native=False, history_window_days=365),
        ),
        currencies=("BTC", "ETH", "USDT", "USD", "GEL"),
        provider_codes={"BTC": "bitcoin", "ETH": "ethereum", "USDT": "tether"},
        dev_sync=(
            SyncSeed("BTC", "GEL", DAILY, days_back=300),
            SyncSeed("BTC", "USD", MONTHLY, days_back=300, is_active=False),
        ),
    ),
)
