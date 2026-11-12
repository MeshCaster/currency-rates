from collections.abc import Callable
from datetime import date
from uuid import UUID

from application.ports import SyncConfigurationRepository
from application.services.rate.models import SyncConfigurationView
from core.clock import utc_today
from core.pagination import Page
from domain.models import SyncConfig


class SyncConfigurationQueryService:
    def __init__(self, configs: SyncConfigurationRepository,
                 today: Callable[[], date] = utc_today) -> None:
        self._configs = configs
        self._today = today

    async def list(self, *, provider: str | None = None, is_active: bool | None = None,
                   page: int = 1, size: int = 50) -> Page[SyncConfigurationView]:
        found = await self._configs.search(provider=provider, is_active=is_active,
                                           page=page, size=size)
        today = self._today()
        return Page([self._view(c, today) for c in found.items], found.total, found.page,
                    found.size)

    async def get(self, id: UUID) -> SyncConfigurationView | None:
        config = await self._configs.get(id)
        return self._view(config, self._today()) if config is not None else None

    @staticmethod
    def _view(config: SyncConfig, today: date) -> SyncConfigurationView:
        return SyncConfigurationView(config, config.progress(today))
