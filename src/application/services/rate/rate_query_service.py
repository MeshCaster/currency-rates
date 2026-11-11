from application.ports import RateRepository
from core.pagination import Page
from domain.models import Rate

class RateQueryService:
    def __init__(self, repository: RateRepository) -> None:
        self._repository = repository

    async def latest(self, base: str, quote: str) -> Rate | None:
        return await self._repository.latest(base, quote)

    async def history(self, base: str, quote: str, page: int = 1, size: int = 50) -> Page[Rate]:
        return await self._repository.history(base, quote, page=page, size=size, official_only=False)

    async def list_pairs(self) -> list[tuple[str, str]]:
        return await self._repository.list_pairs(include_cross=True)
