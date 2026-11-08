from typing import Protocol

from domain.models import Rate


class RateProvider(Protocol):

    name: str

    async def get_rate(self, base: str, quote: str) -> Rate: ...
