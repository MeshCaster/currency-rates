import logging

from core.configuration.settings import Settings
from core.jobs.base import Job
from core.jobs.heartbeat import HeartbeatJob
from core.lifespan import AppState
from host.jobs.history_sync import SyncConfigurationJob
from host.jobs.price_alerts import PriceAlertJob
from host.jobs.subscription_emails import SubscriptionEmailJob
from host.providers import HistoryProviders, smtp_mailer

logger = logging.getLogger(__name__)


def build_jobs(settings: Settings, state: AppState) -> list[Job]:
    worker = settings.worker
    jobs: list[Job] = [HeartbeatJob(worker.heartbeat_file, worker.heartbeat_interval_seconds)]

    db = state["db"]
    if settings.history_sync.enabled:
        if db is None:
            logger.warning("History sync disabled: DATABASE__URL is not configured")
        else:
            jobs.append(SyncConfigurationJob(db, HistoryProviders(state["http_client"]),
                                             settings.history_sync))
    if settings.alerts.enabled:
        if db is None:
            logger.warning("Price alerts disabled: DATABASE__URL is not configured")
        else:
            jobs.append(PriceAlertJob(db, HistoryProviders(state["http_client"]),
                                      settings.alerts))
    if settings.notifications.enabled:
        mailer = smtp_mailer(settings.smtp)
        if db is None or mailer is None:
            logger.warning("Subscription emails disabled: DATABASE__URL or SMTP__HOST is not "
                           "configured")
        else:
            jobs.append(SubscriptionEmailJob(db, HistoryProviders(state["http_client"]), mailer,
                                             settings.notifications))
    return jobs
