from contextlib import asynccontextmanager
from logging.config import dictConfig
from typing import AsyncIterator, Tuple, Dict

import sentry_sdk
from fastapi import APIRouter, FastAPI

from controllers import MediaController
from exceptions import ExceptionRegistrator
from middlewares import ValidateUploadMediaMiddleware
from models.managers import db_session_manager
from routers import media_router, tweets_router, users_router
from settings import settings


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    dictConfig(settings.LOGGING)

    db_session_manager.init(
        engine_url=settings.DB_URL,
        echo_sql=settings.ECHO_SQL,
        init_db=settings.FORCE_INIT,
    )

    MediaController.start_threads()

    await db_session_manager.inspect()

    if settings.SENTRY:
        sentry_sdk.init(
            dsn=settings.SENTRY,
            traces_sample_rate=0.8,
            profiles_sample_rate=0.8,
        )

    yield

    MediaController.stop_threads()
    await db_session_manager.close()


api_prefix: str = "/api"
app = FastAPI(
    debug=settings.DEBUG,
    title=settings.API_NAME,
    version=settings.API_VERSION,
    lifespan=lifespan,
    openapi_url=api_prefix + "/openapi.json",
    docs_url=api_prefix + "/docs",
    redoc_url=api_prefix + "/redoc",
    swagger_ui_oauth2_redirect_url=api_prefix + "/docs/oauth2-redirect",
)

# Exceptions
ExceptionRegistrator(app).register_all()

# Routers
MAIN_ROUTER: APIRouter = APIRouter(prefix=api_prefix)
ROUTERS: Tuple[APIRouter, ...] = (
    users_router,
    tweets_router,
    media_router,
)

for router in ROUTERS:
    MAIN_ROUTER.include_router(router)

app.include_router(MAIN_ROUTER)


# Middlewares
MIDDLEWARES: Dict = {
    ValidateUploadMediaMiddleware: {
        "upload_paths": [app.url_path_for("upload_media")],
        "max_size": settings.MAX_MEDIA_SIZE,
    },
}

for middleware, options in MIDDLEWARES.items():
    app.add_middleware(middleware, **options)
