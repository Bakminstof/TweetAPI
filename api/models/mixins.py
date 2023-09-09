from typing import Any, List, Tuple

from sqlalchemy import Table, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession


class CRUDMixin:
    table: Table | None = None
    default_limit: int = 100

    @classmethod
    async def add_all(
        cls,
        async_session: AsyncSession,
        items: List[Any],
    ) -> List[Any]:
        async_session.add_all(items)
        await async_session.commit()
        return items

    @classmethod
    async def add(
        cls,
        async_session: AsyncSession,
        item: Any,
    ) -> Any:
        async_session.add(item)
        await async_session.commit()
        return item

    @classmethod
    async def delete(
        cls,
        async_session: AsyncSession,
        where: List | Tuple | None = None,
    ) -> bool:
        if not cls.table:
            raise AttributeError(f"{cls.__name__}.table is not set")

        stmt = delete(cls.table)

        if where:
            stmt = stmt.where(*where)

        result = await async_session.execute(stmt)
        await async_session.commit()
        return bool(result.rowcount)

    @classmethod
    async def update(
        cls,
        async_session: AsyncSession,
        instances: List[dict],
    ) -> None:
        if not cls.table:
            raise AttributeError(f"{cls.__name__}.table is not set")

        await async_session.execute(update(cls.table), instances)
        await async_session.commit()

    @classmethod
    async def exists(
        cls,
        async_session: AsyncSession,
        where: List | Tuple,
    ) -> bool:
        if not cls.table:
            raise AttributeError(f"{cls.__name__}.table is not set")

        stmt = select(select(cls.table).where(*where).exists())

        result = await async_session.execute(stmt)
        await async_session.commit()
        return result.one()[0]
