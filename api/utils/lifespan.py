import json
from contextlib import asynccontextmanager
from logging.config import dictConfig
from pathlib import Path
from typing import AsyncIterator, Sequence

import sentry_sdk
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from starlette.routing import BaseRoute
from starlette.staticfiles import StaticFiles

from controllers import MediaController
from models.managers import db_session_manager
from settings import settings


def make_openapi_json(title: str, version: str, routes: Sequence[BaseRoute]) -> None:
    openapi_schema = get_openapi(title=title, version=version, routes=routes)
    openapi_path = Path(settings.STATIC_DIR) / "openapi.json"

    with openapi_path.open(mode="w") as file:
        file.write(json.dumps(openapi_schema))


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    dictConfig(settings.LOGGING)

    db_session_manager.init(
        engine_url=settings.DB_URL,
        echo_sql=settings.ECHO_SQL,
        init_db=settings.FORCE_INIT,
    )

    MediaController.start_threads()

    # await db_session_manager.inspect()

    if settings.DEBUG:
        application.mount(
            settings.STATIC_URL,
            StaticFiles(directory=settings.STATIC_DIR),
            name="static",
        )

    if settings.SENTRY:
        sentry_sdk.init(
            dsn=settings.SENTRY,
            traces_sample_rate=0.8,
            profiles_sample_rate=0.8,
        )

    make_openapi_json(
        settings.API_NAME,
        settings.API_VERSION,
        application.routes,
    )

    yield

    MediaController.stop_threads()
    await db_session_manager.close()
