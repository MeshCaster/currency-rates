import logging

from core.configuration.settings import Settings
from core.jobs.base import Job
from core.jobs.heartbeat import HeartbeatJob
from core.lifespan import AppState
from host.jobs.history_sync import SyncConfigurationJob
from host.providers import HistoryProviders

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
    return jobs
