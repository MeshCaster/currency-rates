import asyncio
import logging
import signal

from core.configuration.settings import Settings, get_settings
from core.jobs.runner import JobRunner
from core.lifespan import app_resources
from core.logging import configure_logging
from host.jobs import build_jobs
from host.seed import seed

logger = logging.getLogger(__name__)


async def run_worker(settings: Settings, *, stop: asyncio.Event | None = None) -> None:
    stop = stop or asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)

    logger.info("Starting %s worker v%s", settings.app_name, settings.app_version,
                extra={"environment": settings.app_env.value})
    async with app_resources(settings) as state:
        if state["db"] is not None:
            await seed(settings, state["db"])
        runner = JobRunner(build_jobs(settings, state))
        await runner.start()
        try:
            await stop.wait()
        finally:
            logger.info("Shutting down worker")
            await runner.stop()


def main() -> None:
    settings = get_settings()
    configure_logging(settings)
    asyncio.run(run_worker(settings))


if __name__ == "__main__":
    main()
