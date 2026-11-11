import dataclasses
from typing import Any, Protocol

from sqlalchemy import inspect


class Mapper[TEntity, TRow](Protocol):
    def to_domain(self, row: TRow) -> TEntity: ...
    def to_values(self, entity: TEntity) -> dict[str, Any]: ...


class DataclassMapper[TEntity, TRow]:

    def __init__(self, entity_type: type[TEntity], row_type: type[TRow]) -> None:
        if not dataclasses.is_dataclass(entity_type):
            raise TypeError(f"{entity_type.__name__} is not a dataclass")
        columns = set(inspect(row_type).columns.keys())
        fields = [f for f in dataclasses.fields(entity_type) if f.init]
        missing = [f.name for f in fields if f.name not in columns]
        if missing:
            raise TypeError(f"{row_type.__name__} has no column(s) for "
                            f"{entity_type.__name__}.{', '.join(missing)}; write a custom Mapper")
        self._entity_type = entity_type
        self._fields = tuple(f.name for f in fields)

    def to_domain(self, row: TRow) -> TEntity:
        return self._entity_type(**{name: getattr(row, name) for name in self._fields})

    def to_values(self, entity: TEntity) -> dict[str, Any]:
        return {name: getattr(entity, name) for name in self._fields}