from typing import Any, List, Tuple

from sqlalchemy import Table, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession


class CRUDMixin:
    table: Table | None = None
    default_limit: int = 100

    def __check_table(self) -> None:
        if not self.table:
            raise AttributeError(f"{self.__name__}.table is not set")

    async def add_all(
        self,
        async_session: AsyncSession,
        items: List[Any],
    ) -> List[Any]:
        async_session.add_all(items)
        await async_session.commit()
        return items

    async def add(
        self,
        async_session: AsyncSession,
        item: Any,
    ) -> Any:
        async_session.add(item)
        await async_session.commit()
        return item

    async def delete(
        self,
        async_session: AsyncSession,
        where: List | Tuple | None = None,
    ) -> bool:
        self.__check_table()

        stmt = delete(self.table)

        if where:
            stmt = stmt.where(*where)

        result = await async_session.execute(stmt)
        await async_session.commit()
        return bool(result.rowcount)

    async def update(
        self,
        async_session: AsyncSession,
        instances: List[dict],
    ) -> None:
        self.__check_table()

        await async_session.execute(update(self.table), instances)
        await async_session.commit()

    async def exists(
        self,
        async_session: AsyncSession,
        where: List | Tuple,
    ) -> bool:
        self.__check_table()

        stmt = select(select(self.table).where(*where).exists())

        result = await async_session.execute(stmt)
        await async_session.commit()
        return result.one()[0]
