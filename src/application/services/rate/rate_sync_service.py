from typing import Iterable

from application import RateProvider, RateRepository, SyncResult, SyncFailure
from domain import Rate

class RateSyncService:

    def __init__(self, provider: RateProvider, repository: RateRepository) -> None:
        self._provider = provider
        self._repository = repository

    async def sync(self, base: str, quote: str) -> Rate:
        rate = await self._provider.get_rate(base, quote)
        await self._repository.add_many([rate])
        return rate

    async def sync_many(self, pairs: Iterable[tuple[str, str]]) -> SyncResult:
        rates: list[Rate] = []
        failures: list[SyncFailure] = []
        for base, quote in pairs:
            try:
                rates.append(await self._provider.get_rate(base, quote))
            except Exception as e:  # noqa: BLE001
                failures.append(SyncFailure(base, quote, str(e)))
        stored = await self._repository.add_many(rates) if rates else 0
        return SyncResult(rates=rates, stored=stored, failures=failures)