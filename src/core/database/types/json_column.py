from typing import Any

from pydantic import TypeAdapter
from sqlalchemy import JSON, Dialect
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.types import TypeDecorator, TypeEngine


class JsonColumn[T](TypeDecorator[T]):

    impl = JSONB(none_as_null=True)
    cache_ok = True

    def __init__(self, model: Any = dict[str, Any]) -> None:
        super().__init__()
        self.model = model
        self._adapter: TypeAdapter[T] = TypeAdapter(model)

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[Any]:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB(none_as_null=True))
        return dialect.type_descriptor(JSON(none_as_null=True))

    def process_bind_param(self, value: T | None, dialect: Dialect) -> Any:
        if value is None:
            return None
        return self._adapter.dump_python(value, mode="json")

    def process_result_value(self, value: Any, dialect: Dialect) -> T | None:
        if value is None:
            return None
        return self._adapter.validate_python(value)


JsonDict = MutableDict.as_mutable(JsonColumn(dict[str, Any]))
