from typing import Annotated
from uuid import UUID

from fastapi import Depends

from application import (
    AlertRuleService,
    AlertService,
    AuthService,
    CurrencyQueryService,
    FeedQueryService,
    IssuedToken,
    SubscriptionService,
    SyncConfigurationAdminService,
    SyncConfigurationQueryService,
)
from core.dependencies import CurrentPrincipalDep, DbSessionDep, SettingsDep
from core.exceptions.unauthorized_error import UnauthorizedError
from core.security.token import create_access_token
from domain.users import User
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
from infrastructure.db.repositories.user_repository import (
    SqlSubscriptionRepository,
    SqlUserRepository,
)


def get_sync_configuration_query_service(session: DbSessionDep) -> SyncConfigurationQueryService:
    return SyncConfigurationQueryService(SqlSyncConfigurationRepository(session))


def get_sync_configuration_admin_service(session: DbSessionDep) -> SyncConfigurationAdminService:
    return SyncConfigurationAdminService(SqlProviderRepository(session),
                                         SqlSyncConfigurationRepository(session),
                                         HistoryProviders.KEYS)


def get_currency_query_service(session: DbSessionDep) -> CurrencyQueryService:
    return CurrencyQueryService(SqlProviderRepository(session))


def get_alert_rule_service(session: DbSessionDep, settings: SettingsDep) -> AlertRuleService:
    return AlertRuleService(SqlAlertRuleRepository(session),
                            SqlSyncConfigurationRepository(session),
                            max_window_minutes=settings.alerts.max_window_minutes)


def get_alert_service(session: DbSessionDep) -> AlertService:
    return AlertService(SqlAlertRepository(session))


def get_auth_service(session: DbSessionDep, settings: SettingsDep) -> AuthService:
    security = settings.security

    def issue(user: User) -> IssuedToken:
        return IssuedToken(create_access_token(str(user.id), security, scopes=user.scopes),
                           expires_in=security.access_token_expire_minutes * 60)

    return AuthService(SqlUserRepository(session), issue)


AuthDep = Annotated[AuthService, Depends(get_auth_service)]


async def get_current_user(principal: CurrentPrincipalDep, auth: AuthDep) -> User:
    try:
        user_id = UUID(principal.sub)
    except ValueError:
        raise UnauthorizedError("this token isn't for a user account",
                                code="not_a_user_token") from None
    return await auth.current_user(user_id)


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def get_subscription_service(session: DbSessionDep) -> SubscriptionService:
    return SubscriptionService(SqlSubscriptionRepository(session),
                               SqlSyncConfigurationRepository(session),
                               SqlProviderRepository(session))


def get_feed_query_service(session: DbSessionDep) -> FeedQueryService:
    return FeedQueryService(SqlSyncConfigurationRepository(session), SqlRateRepository(session),
                            SqlProviderRepository(session))
