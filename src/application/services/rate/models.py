from dataclasses import dataclass

from domain import Rate


@dataclass(frozen=True, slots=True)
class SyncFailure:
    base: str
    quote: str
    error: str


@dataclass(frozen=True, slots=True)
class SyncResult:
    rates: list[Rate]
    stored: int
    failures: list[SyncFailure]

    @property
    def fetched(self) -> int:
        return len(self.rates)

    @property
    def ok(self) -> bool:
        return not self.failures