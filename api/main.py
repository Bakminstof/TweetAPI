from typing import Dict, Tuple

from fastapi import APIRouter, FastAPI

from exceptions import ExceptionRegistrator
from middlewares import ValidateUploadMediaMiddleware
from routers import base_router, media_router, tweets_router, users_router
from settings import settings
from utils.lifespan import lifespan

app: FastAPI = FastAPI(
    debug=settings.DEBUG,
    title=settings.API_NAME,
    version=settings.API_VERSION,
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    swagger_ui_oauth2_redirect_url=None,
    openapi_url=settings.OPENAPI_URL,
)

# Exceptions
ExceptionRegistrator(app).register_all()

# Routers
ROUTERS: Tuple[APIRouter, ...] = (
    users_router,
    tweets_router,
    media_router,
)

for router in ROUTERS:
    base_router.include_router(router)

app.include_router(base_router)


# Middlewares
MIDDLEWARES: Dict = {
    ValidateUploadMediaMiddleware: {
        "upload_paths": [app.url_path_for("upload_media")],
        "max_size": settings.MAX_MEDIA_SIZE,
    },
}

for middleware, options in MIDDLEWARES.items():
    app.add_middleware(middleware, **options)
