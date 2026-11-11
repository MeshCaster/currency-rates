from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Page[T]:
    items: list[T]
    total: int
    page: int
    size: int

    @property
    def pages(self) -> int:
        return max(1, -(-self.total // self.size))

    @property
    def has_next(self) -> bool:
        return self.page < self.pages
