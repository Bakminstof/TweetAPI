from fastapi import APIRouter
from fastapi.openapi.docs import (
    get_redoc_html,
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)
from starlette.responses import HTMLResponse

from settings import settings

base_router: APIRouter = APIRouter(prefix="/api")


@base_router.get("/redoc", include_in_schema=False)
async def redoc_html() -> HTMLResponse:
    return get_redoc_html(
        openapi_url=settings.OPENAPI_URL,
        title=settings.API_NAME + " - ReDoc",
        redoc_js_url=settings.STATIC_URL
        + "/"
        + settings.JS_DIR.name
        + "/redoc.standalone.js",
        redoc_favicon_url=settings.STATIC_URL
        + "/"
        + settings.MEDIA_DIR.name
        + "/docs_favicon.png",
    )


@base_router.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html() -> HTMLResponse:
    return get_swagger_ui_html(
        openapi_url=settings.OPENAPI_URL,
        title=settings.API_NAME + " - Swagger UI",
        oauth2_redirect_url=settings.SWAGGER_UI_OAUTH2_REDIRECT_URL,
        swagger_js_url=settings.STATIC_URL
        + "/"
        + settings.JS_DIR.name
        + "/swagger-ui-bundle.js",
        swagger_css_url=settings.STATIC_URL
        + "/"
        + settings.CSS_DIR.name
        + "/swagger-ui.css",
        swagger_favicon_url=settings.STATIC_URL
        + "/"
        + settings.MEDIA_DIR.name
        + "/docs_favicon.png",
    )


@base_router.get(settings.SWAGGER_UI_OAUTH2_REDIRECT_URL, include_in_schema=False)
async def swagger_ui_redirect() -> HTMLResponse:
    return get_swagger_ui_oauth2_redirect_html()
