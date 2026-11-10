from enum import StrEnum
from typing import Final


class LogFormat(StrEnum):
    TEXT = "text"
    JSON = "json"

class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"

REQUEST_ID_HEADER: Final = "X-Request-ID"
PROBLEM_JSON_MEDIA_TYPE: Final = "application/problem+json"