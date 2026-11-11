from pydantic import BaseModel, Field, field_validator

from core.configuration.security_config import CsvList, _parse_csv_list


class RateSyncSettings(BaseModel):
    enabled: bool = True
    pairs: CsvList = ["USD/GEL", "EUR/GEL"]
    interval_seconds: float = Field(default=10.0, gt=0)

    _split = field_validator("pairs", mode="before")(_parse_csv_list)

    @field_validator("pairs")
    @classmethod
    def _check_pairs(cls, pairs: list[str]) -> list[str]:
        for pair in pairs:
            base, sep, quote = pair.partition("/")
            if not (sep and base and quote):
                raise ValueError(f"pair {pair!r} must look like BASE/QUOTE")
        return [pair.upper() for pair in pairs]

    @property
    def pair_tuples(self) -> list[tuple[str, str]]:
        return [(base, quote) for base, _, quote in (p.partition("/") for p in self.pairs)]
