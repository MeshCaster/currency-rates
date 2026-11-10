from pydantic import BaseModel, field_validator

from core.configuration.security_config import CsvList, _parse_csv_list


class CorsSettings(BaseModel):
    allow_origins: CsvList = []
    allow_credentials: bool = False
    allow_methods: CsvList = ["*"]
    allow_headers: CsvList = ["*"]
    max_age: int = 600

    _split = field_validator("allow_origins", "allow_methods", "allow_headers", mode="before")(
        _parse_csv_list
    )