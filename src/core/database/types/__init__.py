from typing import TYPE_CHECKING, Any

from core.database.types.json_column import JsonColumn, JsonDict
from core.clock import utc_now
from core.database.types.utc_datetime import UtcDateTime

if TYPE_CHECKING:
    from alembic.autogenerate.api import AutogenContext

__all__ = ["JsonColumn", "JsonDict", "UtcDateTime", "render_item", "utc_now"]


def render_item(type_: str, obj: Any, autogen_context: AutogenContext) -> str | bool:
    if type_ != "type":
        return False
    if isinstance(obj, UtcDateTime):
        return "sa.DateTime(timezone=True)"
    if isinstance(obj, JsonColumn):
        autogen_context.imports.add("from sqlalchemy.dialects import postgresql")
        return "postgresql.JSONB(astext_type=sa.Text())"
    return False
