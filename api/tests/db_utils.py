from argparse import Namespace
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Dict, List, Sequence, Tuple
from uuid import uuid4

from alembic.config import Config as AlembicConfig
from sqlalchemy import URL, TextClause, select, text
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import joinedload, load_only, noload

from models.managers import UserManager
from models.mixins import CRUDMixin
from models.schemas import Token, User
from settings import settings


def make_alembic_config(
    cmd_opts: Namespace,
    base_path: str | Path = settings.ROOT_PATH,
) -> AlembicConfig:
    # Replace path to alembic.ini file to absolute
    base_path = Path(base_path)
    if not Path(cmd_opts.config).is_absolute():
        cmd_opts.config = str(base_path.joinpath(cmd_opts.config).absolute())
    config = AlembicConfig(
        file_=cmd_opts.config,
        ini_section=cmd_opts.name,
        cmd_opts=cmd_opts,
    )
    # Replace path to alembic folder to absolute
    alembic_location = config.get_main_option("script_location")
    if not Path(alembic_location).is_absolute():
        config.set_main_option(
            "script_location",
            str(base_path.joinpath(alembic_location).absolute()),
        )
    if cmd_opts.pg_url:
        config.set_main_option("sqlalchemy.URL", cmd_opts.pg_url)
    return config


def alembic_config_from_url(pg_url: str | None = None) -> AlembicConfig:
    """Provides python object, representing alembic.ini file."""
    cmd_options = Namespace(
        config="alembic.ini",  # Config file name
        name="alembic",  # Name of section in .ini file to use for Alembic config
        pg_url=pg_url,  # DB URI
        raiseerr=True,  # Raise a full stack trace on error
        x=None,  # Additional arguments consumed by custom env.py scripts
    )
    return make_alembic_config(cmd_options)


class DBManager:
    __user_manager: UserManager = UserManager()

    def __init__(self) -> None:
        self.__engine_url: URL | None = None
        self.__async_engine: AsyncEngine | None = None

    def __set_engine_url(self, engine_url: str | URL) -> None:
        if not self.__engine_url:
            self.__engine_url = make_url(engine_url)

    def __set_async_engine(self) -> None:
        if not self.__async_engine:
            self.__async_engine = create_async_engine(
                self.__engine_url,
                connect_args=self.__connection_args(self.__engine_url.drivername),
                isolation_level="AUTOCOMMIT",
            )

    @staticmethod
    def __connection_args(drivername: str) -> Dict:
        if "postgresql" in drivername:
            connect_args = {
                "statement_cache_size": 0,
                "prepared_statement_cache_size": 0,
            }
        else:
            connect_args = {}

        return connect_args

    async def create_database(
        self,
        database: str,
        encoding: str = "utf8",
        template: str = "template1",
    ) -> None:
        async with self.__async_engine.begin() as async_conn:
            await async_conn.execute(
                self.__create_database_stmt(database, encoding, template),
            )
            print(f"Create database: [{database}]")

        await self.__async_engine.dispose()

    async def drop_database(self, database: str) -> None:
        async with self.__async_engine.begin() as async_conn:
            version = async_conn.dialect.server_version_info
            await async_conn.execute(self.__disconnect_users_stmt(database, version))
            print(f"Disconnect users from database: [{database}]")

            await async_conn.execute(self.__drop_database_stmt(database))
            print(f"Drop database: [{database}]")

        await self.__async_engine.dispose()

    @asynccontextmanager
    async def create_tmp_database(
        self,
        engine_url: str | URL,
        suffix: str = "",
        **kwargs,
    ) -> AsyncIterator[URL]:
        """Context manager for creating new database and deleting it on exit."""
        tmp_db_name = "_".join([uuid4().hex, "tests_base", suffix])

        engine_url = make_url(engine_url)

        tmp_db_url = URL.create(
            drivername=engine_url.drivername,
            username=engine_url.username,
            password=engine_url.password,
            host=engine_url.host,
            port=engine_url.port,
            database=tmp_db_name,
        )

        self.__set_engine_url(engine_url)
        self.__set_async_engine()

        await self.create_database(tmp_db_name, **kwargs)

        try:
            yield tmp_db_url
        finally:
            await self.drop_database(tmp_db_name)
            # pass

    @staticmethod
    def __disconnect_users_stmt(
        database: str,
        server_version_info: Tuple[int, int],
    ) -> TextClause:
        # Disconnect all users from the database we are dropping.
        pid_column = "pid" if (server_version_info >= (9, 2)) else "procpid"
        return text(
            f"""
            SELECT pg_terminate_backend(pg_stat_activity.{pid_column})
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{database}'
            AND {pid_column} <> pg_backend_pid();
            """,
        )

    @staticmethod
    def __create_database_stmt(database: str, encoding: str, template: str) -> TextClause:
        return text(
            f"CREATE DATABASE \"{database}\" ENCODING '{encoding}' TEMPLATE {template}",
        )

    @staticmethod
    def __drop_database_stmt(database: str) -> TextClause:
        return text(f'DROP DATABASE IF EXISTS "{database}"')

    @classmethod
    async def create_test_users(
        cls,
        names: List[str],
        async_session: AsyncSession,
    ) -> List[User]:
        users = [User(name=name) for name in names]
        async_session.add_all(users)
        await async_session.commit()
        return users

    @classmethod
    async def create_test_tokens(
        cls,
        users: List[User],
        async_session: AsyncSession,
    ) -> List[Token]:
        test_mixin = CRUDMixin()
        test_mixin.table = Token

        options = [
            load_only(User.id, User.name, User.following, User.followers),
            noload(User.tweets),
            joinedload(User.token),
            noload(User.tweets_likes),
        ]

        user_ids = [user.id for user in users]

        stmt = select(User).where(User.id.in_(user_ids)).options(*options)
        result = await async_session.scalars(stmt)
        users: Sequence[User] = result.unique().all()
        await async_session.commit()

        tokens = []

        for user in users:
            tokens.append(Token(api_key=str(uuid4()), user=user))

        await test_mixin.add_all(async_session, tokens)
        return tokens
