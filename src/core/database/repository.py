from typing import Any, ClassVar, Iterable, Protocol, Sequence, cast

from sqlalchemy import (CursorResult, select, update, delete, and_, or_, tuple_, ColumnElement,
                        func)
from sqlalchemy.ext.asyncio.session import AsyncSession

from core.pagination import Page
from core.database.errors import ConcurrencyError, DuplicateError, NotFoundError
from core.database.mapper import Mapper
from core.database.orm import Base


def _dialect_insert(session: AsyncSession) -> Any:
    dialect = session.get_bind().dialect.name
    if dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        return pg_insert
    if dialect == "sqlite":
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert
        return sqlite_insert
    raise NotImplementedError(f"Unsupported dialect {dialect!r}")


async def insert_ignore(session: AsyncSession, row_type: type[Base],
                        rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    insert = _dialect_insert(session)
    result = cast(CursorResult[Any], await session.execute(
        insert(row_type).values(rows).on_conflict_do_nothing()))
    return max(result.rowcount, 0)


async def upsert(session: AsyncSession, row_type: type[Base], rows: list[dict[str, Any]], *,
                 conflict_columns: Sequence[str],
                 update_columns: Sequence[str]) -> int:
    if not rows:
        return 0
    insert = _dialect_insert(session)
    stmt = insert(row_type).values(rows)
    table, new = row_type.__table__, stmt.excluded
    values: dict[str, Any] = {column: new[column] for column in update_columns}
    if "updated_at" in table.c:
        values["updated_at"] = func.now()
    stmt = stmt.on_conflict_do_update(
        index_elements=list(conflict_columns), set_=values,
        where=or_(*(table.c[column].is_distinct_from(new[column]) for column in update_columns)))
    result = cast(CursorResult[Any], await session.execute(stmt))
    return max(result.rowcount, 0)


class Repository[TEntity, TId](Protocol):
    async def get(self, id: TId) -> TEntity | None: ...
    async def get_or_raise(self, id: TId) -> TEntity: ...
    async def get_many(self, ids: Iterable[TId]) -> list[TEntity]: ...
    async def paginate(self, page: int = 1, size: int = 50) -> Page[TEntity]: ...
    async def exists(self, id: TId) -> bool: ...
    async def count(self) -> int: ...
    async def add(self, entity: TEntity) -> None: ...
    async def update(self, entity: TEntity) -> None: ...
    async def delete(self, id: TId) -> None: ...


class SqlAlchemyRepository[TEntity, TId, TRow: Base]:

    row_type: ClassVar[type[Base]]
    mapper: ClassVar[Mapper[Any, Any]]
    id_columns: ClassVar[tuple[str, ...]] = ("id",)
    version_column: ClassVar[str | None] = "version"
    managed_columns: ClassVar[tuple[str, ...]] = ("created_at", "updated_at")

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, id: TId) -> TEntity | None:
        row = await self._session.get(self.row_type, id)
        return self.mapper.to_domain(row) if row is not None else None

    async def get_or_raise(self, id: TId) -> TEntity:
        entity = await self.get(id)
        if entity is None:
            raise NotFoundError.for_(self.row_type.__name__, id)
        return entity

    async def get_many(self, ids: Iterable[TId]) -> list[TEntity]:
        ids = list(ids)
        if not ids:
            return []
        if len(self.id_columns) == 1:
            return await self._find(self._id_cols[0].in_([self._as_tuple(i)[0] for i in ids]))
        return await self._find(tuple_(*self._id_cols).in_([self._as_tuple(i) for i in ids]))

    async def paginate(self, page: int = 1, size: int = 50) -> Page[TEntity]:
        return await self._page(page=page, size=size)

    async def exists(self, id: TId) -> bool:
        return await self._session.scalar(select(select(1).where(self._id_where(id)).exists())) or False

    async def count(self) -> int:
        return await self._count()

    async def add(self, entity: TEntity) -> None:
        values = self._values_of(entity)
        if self.version_column and self.version_column in values:
            values[self.version_column] = 1
        id = self._id_of(values)
        if await self.exists(id):
            raise DuplicateError.for_(self.row_type.__name__, id)
        row = self.row_type(**values)
        self._session.add(row)
        await self._session.flush()
        self._session.expunge(row)
        self._bump_version(entity)

    async def update(self, entity: TEntity) -> None:
        values = self._values_of(entity)
        id = self._id_of(values)
        for column in self.id_columns:
            values.pop(column, None)
        stmt = update(self.row_type).where(self._id_where(id))

        if self.version_column and self.version_column in values:
            current = values[self.version_column]
            values[self.version_column] = current + 1
            stmt = stmt.where(getattr(self.row_type, self.version_column) == current)

        result = await self._session.execute(stmt.values(**values).execution_options(synchronize_session=False))
        if result.rowcount == 0:
            if await self.exists(id):
                raise ConcurrencyError.for_(self.row_type.__name__, id)
            raise NotFoundError.for_(self.row_type.__name__, id)
        self._bump_version(entity)

    async def delete(self, id: TId) -> None:
        result = await self._session.execute(
            delete(self.row_type).where(self._id_where(id)).execution_options(synchronize_session=False))
        if result.rowcount == 0:
            raise NotFoundError.for_(self.row_type.__name__, id)

    @property
    def _id_cols(self) -> tuple[Any, ...]:
        return tuple(getattr(self.row_type, name) for name in self.id_columns)

    def _values_of(self, entity: TEntity) -> dict[str, Any]:
        values = self.mapper.to_values(entity)
        for column in self.managed_columns:
            values.pop(column, None)
        return values

    @staticmethod
    def _as_tuple(id: Any) -> tuple[Any, ...]:
        return id if isinstance(id, tuple) else (id,)

    def _id_of(self, values: dict[str, Any]) -> Any:
        ids = tuple(values[name] for name in self.id_columns)
        return ids if len(ids) > 1 else ids[0]

    def _id_where(self, id: TId) -> ColumnElement[bool]:
        return and_(*(col == value for col, value in zip(self._id_cols, self._as_tuple(id))))

    async def _find(self, *criteria: ColumnElement[bool], order_by: Sequence[Any] = (),
                    limit: int | None = None, for_update: bool = False) -> list[TEntity]:
        stmt = select(self.row_type).where(*criteria).order_by(*order_by)
        if limit is not None:
            stmt = stmt.limit(limit)
        if for_update:
            stmt = stmt.with_for_update(skip_locked=True)
        rows = (await self._session.scalars(stmt)).all()
        return [self.mapper.to_domain(r) for r in rows]

    async def _find_one(self, *criteria: ColumnElement[bool]) -> TEntity | None:
        found = await self._find(*criteria, limit=2)
        if len(found) > 1:
            raise LookupError(f"Expected one {self.row_type.__name__}, found several")
        return found[0] if found else None

    async def _count(self, *criteria: ColumnElement[bool]) -> int:
        stmt = select(func.count()).select_from(self.row_type).where(*criteria)
        return await self._session.scalar(stmt) or 0

    async def _page(self, *criteria: ColumnElement[bool], page: int = 1, size: int = 50,
                    order_by: Sequence[Any] = ()) -> Page[TEntity]:
        if page < 1 or not 1 <= size <= 1000:
            raise ValueError("page must be >= 1 and size between 1 and 1000")
        order = order_by or self._id_cols
        stmt = (select(self.row_type).where(*criteria).order_by(*order)
                .offset((page - 1) * size).limit(size))
        rows = (await self._session.scalars(stmt)).all()
        return Page([self.mapper.to_domain(r) for r in rows], await self._count(*criteria), page, size)

    async def _insert_ignore(self, rows: list[dict[str, Any]]) -> int:
        return await insert_ignore(self._session, self.row_type, rows)

    def _bump_version(self, entity: TEntity) -> None:
        if self.version_column and hasattr(entity, self.version_column):
            setattr(entity, self.version_column, getattr(entity, self.version_column) + 1)
