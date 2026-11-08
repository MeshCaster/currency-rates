import asyncio
from datetime import date

from rates_provider_integration.errors import RateProviderError
from rates_provider_integration.http_clients import default_client
from rates_provider_integration.crypto.binance import BinanceProvider
from rates_provider_integration.crypto.coinbase import CoinbaseProvider
from rates_provider_integration.crypto.coin_gecko import CoinGeckoProvider
from rates_provider_integration.crypto.kraken import KrakenProvider


async def main() -> None:
    async with default_client() as http:
        binance = BinanceProvider(http)
        kraken = KrakenProvider(http)
        coinbase = CoinbaseProvider(http)
        coingecko = CoinGeckoProvider(http)

        print(await binance.get_rate("BTC", "USDT"))
        print(await binance.get_rates([("BTC", "USDT"), ("ETH", "USDT")]))

        print(await kraken.get_rate("BTC", "USD"))
        ticker = await kraken.get_ticker("BTC", "USD")
        print("Kraken bid/ask/mid:", ticker.bid, ticker.ask, ticker.mid)

        print(await coinbase.get_rate("BTC", "USD"))
        print(await coinbase.get_rate("BTC", "USD", on=date(2026, 1, 1)))

        for rate in await coingecko.get_rates(["BTC", "ETH", "USDT"], ["USD", "GEL"]):
            print(rate)

        results = await asyncio.gather(
            binance.get_rate("BTC", "USDT"),
            kraken.get_rate("BTC", "USD"),
            coinbase.get_rate("BTC", "USD"),
            return_exceptions=True,
        )
        for r in results:
            print("  ", r if not isinstance(r, RateProviderError) else f"failed: {r}")


if __name__ == "__main__":
    asyncio.run(main())