import logging
from collections.abc import Sequence

from host.jobs.base import Job

logger = logging.getLogger(__name__)


class JobRunner:
    def __init__(self, jobs: Sequence[Job]) -> None:
        self._jobs = list(jobs)

    async def start(self) -> None:
        for job in self._jobs:
            await job.start()

    async def stop(self) -> None:
        for job in reversed(self._jobs):
            try:
                await job.stop()
            except Exception:
                logger.exception("failed to stop %s", job.name)
