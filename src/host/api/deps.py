from fastapi import Depends, Request

from application.ports import RateProvider, RateRepository
from application import (AlertRuleService, AlertService, HistoricalRateSyncService,
                         RateQueryService,
                         SyncConfigurationAdminService, SyncConfigurationQueryService)
from core.dependencies import DbSessionDep, SettingsDep
from host.providers import HistoryProviders
from infrastructure.db.repositories.alert_repository import (
    SqlAlertRepository,
    SqlAlertRuleRepository,
)
from infrastructure.db.repositories.provider_repository import SqlProviderRepository
from infrastructure.db.repositories.rate_repository import SqlRateRepository
from infrastructure.db.repositories.sync_configuration_repository import (
    SqlSyncConfigurationRepository,
)


def get_repository(session: DbSessionDep) -> RateRepository:
    return SqlRateRepository(session)


def get_provider(request: Request) -> RateProvider:
    return request.state.provider


def get_query_service(repository: RateRepository = Depends(get_repository)) -> RateQueryService:
    return RateQueryService(repository)


def get_historical_sync_service(repository: RateRepository = Depends(get_repository),
                                provider: RateProvider = Depends(get_provider)) -> HistoricalRateSyncService:
    return HistoricalRateSyncService(provider, repository)


def get_sync_configuration_query_service(session: DbSessionDep) -> SyncConfigurationQueryService:
    return SyncConfigurationQueryService(SqlSyncConfigurationRepository(session))


def get_sync_configuration_admin_service(session: DbSessionDep) -> SyncConfigurationAdminService:
    return SyncConfigurationAdminService(SqlProviderRepository(session),
                                         SqlSyncConfigurationRepository(session),
                                         HistoryProviders.KEYS)


def get_alert_rule_service(session: DbSessionDep, settings: SettingsDep) -> AlertRuleService:
    return AlertRuleService(SqlAlertRuleRepository(session),
                            SqlSyncConfigurationRepository(session),
                            max_window_minutes=settings.alerts.max_window_minutes)


def get_alert_service(session: DbSessionDep) -> AlertService:
    return AlertService(SqlAlertRepository(session))
