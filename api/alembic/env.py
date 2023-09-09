import asyncio
from contextvars import ContextVar
from logging.config import fileConfig
from typing import Any
from urllib.parse import quote_plus

from sqlalchemy import URL, pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from alembic.runtime.environment import EnvironmentContext
from models.schemas import Base
from settings import settings

ctx_var: ContextVar[dict[str, Any]] = ContextVar("ctx_var")

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


target_metadata = Base.metadata

represented_password = quote_plus(settings.DB_URL.password).replace("%", "%%")

url = URL.create(
    drivername=settings.DB_URL.drivername,
    username=settings.DB_URL.username,
    password=represented_password,
    host=settings.DB_URL.host,
    port=settings.DB_URL.port,
    database=settings.DB_URL.database,
)

config.set_main_option("sqlalchemy.URL", url.render_as_string(False))


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    current_url = config.get_main_option("sqlalchemy.URL", None)
    context.configure(
        url=current_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    try:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()

    except AttributeError:
        context_data = ctx_var.get()

        with EnvironmentContext(
            config=context_data["config"],
            script=context_data["script"],
            **context_data["opts"],
        ):
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    ctx_var.set(
        {
            "config": context.config,
            "script": context.script,
            "opts": context._proxy.context_opts,  # noqa
        },
    )

    try:
        asyncio.get_running_loop()

        from tests import conftest

        conftest.MIGRATION_TASK = asyncio.create_task(run_async_migrations())

    except RuntimeError:
        asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
