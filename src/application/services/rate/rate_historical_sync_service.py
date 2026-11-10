from datetime import date, timedelta

from application import HistoricalRateProvider, RateRepository
from application.services.rate.models import SyncResult, SyncFailure
from domain import Rate


class HistoricalRateSyncService:

    def __init__(self, provider: HistoricalRateProvider, repository: RateRepository) -> None:
        self._provider = provider
        self._repository = repository

    async def sync_range(self, base: str, quote: str, since: date, until: date) -> SyncResult:
        if since > until:
            raise ValueError("since must be on or before until")
        rates: list[Rate] = []
        failures: list[SyncFailure] = []
        day = since
        while day <= until:
            try:
                rates.append(await self._provider.get_rate(base, quote, day))
            except Exception as e:  # noqa: BLE001
                failures.append(SyncFailure(base, quote, f"{day.isoformat()}: {e}"))
            day += timedelta(days=1)
        stored = await self._repository.add_many(rates) if rates else 0
        return SyncResult(rates=rates, stored=stored, failures=failures)
