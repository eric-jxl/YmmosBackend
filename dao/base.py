from __future__ import annotations

from typing import Any, Dict, Generic, List, Optional, Tuple, TypeVar
from datetime import UTC, datetime

from sqlalchemy import and_, asc, desc, or_
from sqlmodel import SQLModel, col, select
from sqlmodel.ext.asyncio.session import AsyncSession

T = TypeVar("T", bound=SQLModel)


class BaseDAO(Generic[T]):
    def __init__(self, model: type[T]):
        self.model = model

    def _build_conditions(
            self,
            *,
            filters: Dict[str, Any] | None = None,
            like_filters: Dict[str, str] | None = None,
            range_filters: Dict[str, Tuple[Any | None, Any | None]] | None = None,
            or_filters: List[Dict[str, Any]] | None = None,
    ) -> List[Any]:
        conditions: List[Any] = []

        for field_name, value in (filters or {}).items():
            if value is None:
                continue
            field = getattr(self.model, field_name, None)
            if field is None:
                raise AttributeError(f"{self.model.__name__} has no field '{field_name}'")
            conditions.append(field == value)

        for field_name, keyword in (like_filters or {}).items():
            if not keyword:
                continue
            field = getattr(self.model, field_name, None)
            if field is None:
                raise AttributeError(f"{self.model.__name__} has no field '{field_name}'")
            conditions.append(col(field).like(f"%{keyword}%"))

        for field_name, (start, end) in (range_filters or {}).items():
            field = getattr(self.model, field_name, None)
            if field is None:
                raise AttributeError(f"{self.model.__name__} has no field '{field_name}'")
            if start is not None:
                conditions.append(field >= start)
            if end is not None:
                conditions.append(field <= end)

        if or_filters:
            or_expressions: List[Any] = []
            for item in or_filters:
                for field_name, value in item.items():
                    if value is None:
                        continue
                    field = getattr(self.model, field_name, None)
                    if field is None:
                        raise AttributeError(f"{self.model.__name__} has no field '{field_name}'")
                    or_expressions.append(field == value)
            if or_expressions:
                conditions.append(or_(*or_expressions))

        return conditions

    def _apply_order(self, statement: Any, order_by: List[Tuple[str, str]] | None = None) -> Any:
        if not order_by:
            return statement

        for field_name, direction in order_by:
            field = getattr(self.model, field_name, None)
            if field is None:
                raise AttributeError(f"{self.model.__name__} has no field '{field_name}'")
            statement = statement.order_by(desc(field) if direction.lower() == "desc" else asc(field))
        return statement

    @classmethod
    async def create(cls, session: AsyncSession, obj: T) -> T:
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj

    async def get_by_id(self, session: AsyncSession, obj_id: int) -> Optional[T]:
        return await session.get(self.model, obj_id)

    async def list(self, session: AsyncSession, skip: int = 0, limit: int = 100) -> List[T]:
        statement = select(self.model)
        if hasattr(self.model, "created_at"):
            statement = statement.order_by(desc(getattr(self.model, "created_at")))
        statement = statement.offset(skip).limit(limit)
        result = await session.exec(statement)
        return list(result.all())

    async def query_list(
            self,
            session: AsyncSession,
            *,
            filters: Dict[str, Any] | None = None,
            like_filters: Dict[str, str] | None = None,
            range_filters: Dict[str, Tuple[Any | None, Any | None]] | None = None,
            or_filters: List[Dict[str, Any]] | None = None,
            order_by: List[Tuple[str, str]] | None = None,
            skip: int = 0,
            limit: int = 100,
    ) -> List[T]:
        statement = select(self.model)
        conditions = self._build_conditions(
            filters=filters,
            like_filters=like_filters,
            range_filters=range_filters,
            or_filters=or_filters,
        )
        if conditions:
            statement = statement.where(and_(*conditions))
        statement = self._apply_order(statement, order_by)
        statement = statement.offset(skip).limit(limit)

        result = await session.exec(statement)
        return list(result.all())

    async def query_first(
            self,
            session: AsyncSession,
            *,
            filters: Dict[str, Any] | None = None,
            like_filters: Dict[str, str] | None = None,
            range_filters: Dict[str, Tuple[Any | None, Any | None]] | None = None,
            or_filters: List[Dict[str, Any]] | None = None,
            order_by: List[Tuple[str, str]] | None = None,
    ) -> Optional[T]:
        rows = await self.query_list(
            session,
            filters=filters,
            like_filters=like_filters,
            range_filters=range_filters,
            or_filters=or_filters,
            order_by=order_by,
            skip=0,
            limit=1,
        )
        return rows[0] if rows else None

    async def update(self, session: AsyncSession, obj_id: int, obj_in: dict[str, Any]) -> Optional[T]:
        db_obj = await session.get(self.model, obj_id)
        if db_obj is None:
            return None

        for key, value in obj_in.items():
            if value is not None:
                setattr(db_obj, key, value)

        # 统一更新时间字段。
        if hasattr(db_obj, "updated_at"):
            setattr(db_obj, "updated_at", datetime.now(UTC))

        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def delete(self, session: AsyncSession, obj_id: int) -> bool:
        db_obj = await session.get(self.model, obj_id)
        if db_obj is None:
            return False

        await session.delete(db_obj)
        await session.commit()
        return True

    async def get_by_field(self, session: AsyncSession, field_name: str, field_value: Any) -> Optional[T]:
        field = getattr(self.model, field_name, None)
        if field is None:
            raise AttributeError(f"{self.model.__name__} has no field '{field_name}'")

        statement = select(self.model).where(field == field_value)
        result = await session.exec(statement)
        return result.first()
