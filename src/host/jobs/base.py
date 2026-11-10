import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class Job(Protocol):
    name: str

    async def start(self) -> None: ...
    async def stop(self) -> None: ...


class PeriodicJob(ABC):

    def __init__(self, interval_seconds: float) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be > 0")
        self._interval = interval_seconds
        self._task: asyncio.Task[None] | None = None

    @property
    def name(self) -> str:
        return type(self).__name__

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._loop(), name=self.name)

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def _loop(self) -> None:
        logger.info("%s started (every %ss)", self.name, self._interval)
        try:
            while True:
                try:
                    await self.run_once()
                except Exception:
                    logger.exception("%s iteration failed", self.name)
                await asyncio.sleep(self._interval)
        except asyncio.CancelledError:
            logger.info("%s stopped", self.name)
            raise

    @abstractmethod
    async def run_once(self) -> None: ...
