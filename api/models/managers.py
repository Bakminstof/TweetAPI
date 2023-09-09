from contextlib import asynccontextmanager
from logging import getLogger
from typing import AsyncGenerator, AsyncIterator, Dict, List, Sequence, Any

from sqlalchemy import MetaData, inspect, make_url, select
from sqlalchemy.engine.url import URL
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import joinedload, load_only, noload
from sqlalchemy.util import FacadeDict

from models.mixins import CRUDMixin
from models.schemas import Base, Like, Media, Token, Tweet, TweetMedia, User


class DatabaseAsyncSessionManager:
    tables: FacadeDict = Base.metadata.tables
    metadata: MetaData = Base.metadata

    logger = getLogger(__name__)

    def __init__(self) -> None:
        self._engine_url: URL | str | None = None
        self._init_db: bool = False
        self._async_engine: AsyncEngine | None = None
        self._async_sessionmaker: async_sessionmaker[AsyncSession] | None = None

    def init(
        self,
        engine_url: URL | str,
        connect_args: Dict | None = None,
        echo_sql: bool = False,
        init_db: bool = False,
    ) -> None:
        self._engine_url = make_url(engine_url)

        if not connect_args:
            connect_args = {}

        if "postgresql" in self._engine_url.drivername:
            connect_args.update(
                {
                    "statement_cache_size": 0,
                    "prepared_statement_cache_size": 0,
                },
            )

        self._init_db = init_db

        self._async_engine: AsyncEngine = create_async_engine(
            self._engine_url,
            echo=echo_sql,
            connect_args=connect_args,
        )
        self._async_sessionmaker: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self._async_engine,
            expire_on_commit=False,
        )

    async def __initialise_db(self) -> None:
        async with self.connect() as conn:
            await conn.run_sync(self.metadata.create_all)

        self.logger.warning("Database is initialized")

    async def close(self) -> None:
        if self._async_engine is None:
            return
        await self._async_engine.dispose()
        self._async_engine = None
        self._async_sessionmaker = None

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        if self._async_sessionmaker is None:
            raise IOError(f"{self} is not initialized")

        async with self._async_sessionmaker() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[AsyncConnection]:
        if self._async_engine is None:
            raise IOError(f"{self} is not initialized")

        async with self._async_engine.begin() as connection:
            try:
                yield connection
            except Exception:
                await connection.rollback()
                raise

    async def __check_missing_tables(
        self,
        missing_tables: List[str],
    ) -> None:
        if missing_tables:
            if self._init_db:
                await self.__initialise_db()
            else:
                exc_text = f"Tables not found: [{', '.join(missing_tables)}]"
                self.logger.critical(exc_text)
                raise ValueError(exc_text)

    def __check_tables(self, database_tables: List[str]) -> List[str]:
        self.logger.debug("Checking tables...")

        missing_tables = []

        for table in self.tables:
            if table not in database_tables:
                missing_tables.append(table)

        if missing_tables:
            self.logger.warning(
                "Tables (%s) not in database tables (%s).",
                ", ".join(missing_tables),
                database_tables,
            )

        return missing_tables

    async def inspect(self) -> None:
        async with self.connect() as async_conn:
            tables = await async_conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_table_names(),
            )
            await self.__check_missing_tables(self.__check_tables(tables))

        self.logger.debug("Database connected")

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        name = self.__class__.__name__
        driver = self._engine_url.drivername
        database = self._engine_url.database
        return f"{name}[{driver}]:{database}"


class TweetManager(CRUDMixin):
    table = Tweet

    async def get_tweets(
        self,
        async_session: AsyncSession,
        order_by: Any | None = None,
        limit: int = None,
    ) -> Sequence[Tweet]:
        """
        Loaded fields:
        id, content, author(id, name), likes(user_id, name), attachments(id)
        """
        options = [
            joinedload(Tweet.author).load_only(User.id, User.name),
            joinedload(Tweet.author).noload(User.tweets),
            joinedload(Tweet.author).noload(User.tweets_likes),
            joinedload(Tweet.author).noload(User.token),
            joinedload(Tweet.likers).joinedload(Like.liker).load_only(User.id, User.name),
            joinedload(Tweet.likers).joinedload(Like.liker).noload(User.tweets),
            joinedload(Tweet.likers).joinedload(Like.liker).noload(User.tweets_likes),
            joinedload(Tweet.likers).joinedload(Like.liker).noload(User.token),
            joinedload(Tweet.attachments)
            .joinedload(TweetMedia.media_item)
            .load_only(Media.id),
        ]

        stmt = (
            select(self.table)
            .options(*options)
            .order_by(order_by or self.table.id)
            .limit(limit or self.default_limit)
        )

        result = await async_session.scalars(stmt)
        result = result.unique().all()
        await async_session.commit()

        return result

    async def get_tweet_with_author_id(
        self,
        async_session: AsyncSession,
        tweet_id: int,
        order_by: Any | None = None,
        limit: int = None,
    ) -> Tweet | None:
        """
        Loaded fields:
        id, author_id, author(id)
        """
        options = [
            load_only(Tweet.id, Tweet.author_id),
            joinedload(Tweet.author).load_only(User.id).noload(User.tweets),
            joinedload(Tweet.author).noload(User.token),
            joinedload(Tweet.author).noload(User.tweets_likes),
            noload(Tweet.likers),
            noload(Tweet.attachments),
        ]

        stmt = (
            select(self.table)
            .where(Tweet.id == tweet_id)
            .options(*options)
            .order_by(order_by or self.table.id)
            .limit(limit or self.default_limit)
        )

        result = await async_session.scalar(stmt)
        await async_session.commit()
        return result


class UserManager(CRUDMixin):
    table = User

    async def get_user_detail(
        self,
        async_session: AsyncSession,
        user_id: int,
        order_by: Any | None = None,
        limit: int = None,
    ) -> User | None:
        """
        Loaded fields:
        id, name, following, followers
        """
        options = [
            load_only(User.id, User.name, User.following, User.followers),
            noload(User.tweets),
            noload(User.token),
            noload(User.tweets_likes),
        ]

        stmt = (
            select(self.table)
            .where(User.id == user_id)
            .options(*options)
            .order_by(order_by or self.table.id)
            .limit(limit or self.default_limit)
        )

        result = await async_session.scalar(stmt)
        await async_session.commit()
        return result

    async def get_user_by_api_key(
        self,
        api_key: str,
        async_session: AsyncSession,
        order_by: Any | None = None,
        limit: int = None,
    ) -> User | None:
        """
        Loaded fields:
        id, name, following, followers, token(api_key)
        """
        options = [
            load_only(User.id, User.name, User.following, User.followers),
            joinedload(User.token).load_only(Token.api_key),
            noload(User.tweets),
            noload(User.tweets_likes),
        ]

        stmt = (
            select(self.table)
            .where(User.token.has(api_key=api_key))
            .options(*options)
            .order_by(order_by or self.table.id)
            .limit(limit or self.default_limit)
        )

        result = await async_session.scalar(stmt)
        await async_session.commit()
        return result


class LikeManager(CRUDMixin):
    table = Like


class TweetMediaManager(CRUDMixin):
    table = TweetMedia


class MediaManager(CRUDMixin):
    table = Media

    async def get_media(
        self,
        async_session: AsyncSession,
        media_ids: List[int],
        order_by: Any | None = None,
        limit: int = None,
    ) -> Sequence[Media]:
        """
        Loaded fields:
        id, file
        """
        options = [
            load_only(Media.id, Media.file),
            noload(Media.tweet_item),
        ]

        stmt = (
            select(self.table)
            .where(Media.id.in_(media_ids))
            .options(*options)
            .order_by(order_by or self.table.id)
            .limit(limit or self.default_limit)
        )

        result = await async_session.scalars(stmt)
        await async_session.commit()
        return result.unique().all()


db_session_manager = DatabaseAsyncSessionManager()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with db_session_manager.session() as session:
        yield session
