from application.ports import ProviderCatalog
from domain.models import Currency


class CurrencyQueryService:
    def __init__(self, catalog: ProviderCatalog) -> None:
        self._catalog = catalog

    async def all(self) -> list[Currency]:
        return await self._catalog.currencies()
