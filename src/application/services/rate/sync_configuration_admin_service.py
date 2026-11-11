import uuid
from collections.abc import Callable, Collection
from datetime import date

from application.ports import ProviderCatalog, SyncConfigurationRepository
from application.services.rate.models import NewSyncConfiguration, SyncConfigurationView
from application.services.rate.sync_configuration_query_service import utc_today
from core.exceptions.conflict_error import ConflictError
from domain.enums import IntervalKind
from domain.errors import InvalidSyncConfigurationError, UnsupportedSyncError
from domain.models import SyncConfig


class SyncConfigurationAdminService:

    def __init__(self, catalog: ProviderCatalog, configs: SyncConfigurationRepository,
                 syncable: Collection[str], today: Callable[[], date] = utc_today) -> None:
        self._catalog = catalog
        self._configs = configs
        self._syncable = syncable
        self._today = today

    async def create(self, new: NewSyncConfiguration) -> SyncConfigurationView:
        base, quote = new.base.upper(), new.quote.upper()
        if base == quote:
            raise InvalidSyncConfigurationError("base and quote must differ")
        if new.date_to is not None and new.date_to < new.date_from:
            raise InvalidSyncConfigurationError("date_to must be on or after date_from")
        if new.interval is not IntervalKind.DAILY:
            raise UnsupportedSyncError(f"{new.interval} sync is not supported yet")

        provider = await self._catalog.get_by_key(new.provider)
        if provider is None:
            raise InvalidSyncConfigurationError(f"unknown provider {new.provider!r}")
        if not provider.is_active:
            raise InvalidSyncConfigurationError(f"provider {provider.key!r} is switched off")
        if provider.key not in self._syncable:
            raise UnsupportedSyncError(f"provider {provider.key!r} has no history integration yet")

        capability = provider.interval(new.interval)
        if capability is None:
            raise InvalidSyncConfigurationError(
                f"provider {provider.key!r} doesn't serve {new.interval} rates")
        today = self._today()
        earliest = capability.earliest(today)
        if earliest is not None and new.date_from < earliest:
            raise InvalidSyncConfigurationError(
                f"provider {provider.key!r} serves {new.interval} rates from {earliest} only")

        unsupported = [c for c in (base, quote)
                       if not await self._catalog.supports_currency(provider.id, c)]
        if unsupported:
            raise InvalidSyncConfigurationError(
                f"provider {provider.key!r} doesn't list {', '.join(unsupported)}")
        if await self._configs.exists_for(provider.id, base, quote, new.interval):
            raise ConflictError(
                f"provider {provider.key!r} already syncs {base}/{quote} {new.interval}",
                code="sync_configuration_exists")

        config = SyncConfig(
            id=uuid.uuid7(), provider_id=provider.id, provider=provider.key, base=base,
            quote=quote, interval=new.interval, date_from=new.date_from, date_to=new.date_to,
            is_active=new.is_active, options=dict(new.options) if new.options else None)
        await self._configs.add(config)
        return SyncConfigurationView(config, config.progress(today))
