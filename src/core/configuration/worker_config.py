import tempfile
from pathlib import Path

from pydantic import BaseModel, Field


class WorkerSettings(BaseModel):
    heartbeat_file: Path = Path(tempfile.gettempdir()) / "currency-rates-worker.heartbeat"
    heartbeat_interval_seconds: float = Field(default=15.0, gt=0)
