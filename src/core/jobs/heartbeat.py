import sys
import time
from pathlib import Path

from core.jobs.base import PeriodicJob


class HeartbeatJob(PeriodicJob):
    def __init__(self, path: Path, interval_seconds: float) -> None:
        super().__init__(interval_seconds)
        self._path = path

    async def run_once(self) -> None:
        self._path.touch()


def is_fresh(path: Path, max_age_seconds: float) -> bool:
    try:
        return time.time() - path.stat().st_mtime <= max_age_seconds
    except FileNotFoundError:
        return False


if __name__ == "__main__":
    sys.exit(0 if is_fresh(Path(sys.argv[1]), float(sys.argv[2])) else 1)
