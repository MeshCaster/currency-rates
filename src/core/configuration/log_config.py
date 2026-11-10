from pydantic import BaseModel

from core.constants import LogFormat

class LogSettings(BaseModel):
    level: str = "INFO"
    format: LogFormat | None = None
    access_log: bool = True