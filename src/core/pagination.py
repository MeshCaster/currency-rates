from collections.abc import Callable
from dataclasses import dataclass
from typing import Self

from pydantic import BaseModel


@dataclass(frozen=True, slots=True)
class Page[T]:
    items: list[T]
    total: int
    page: int
    size: int



class PageResponse[Item](BaseModel):

    items: list[Item]
    total: int
    page: int
    size: int

    @classmethod
    def of[T](cls, found: Page[T], convert: Callable[[T], Item]) -> Self:
        return cls(items=[convert(i) for i in found.items], total=found.total,
                   page=found.page, size=found.size)
