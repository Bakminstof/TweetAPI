from re import search
from typing import List

from fastapi import Response, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from exceptions import ExceptionHandler, ValidationError


class ValidateUploadMediaMiddleware(BaseHTTPMiddleware):
    _handler = ExceptionHandler()

    SUPPORTED_TYPES = [
        "multipart/form-data",
    ]

    def __init__(
        self,
        app: ASGIApp,
        upload_paths: List[str],
        max_size: int = 5 * 1024 * 1024,  # 5 MB
    ) -> None:
        super().__init__(app)
        self.upload_paths = upload_paths
        self.max_size = max_size

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        scope = request.scope

        if scope["type"] not in ("http",):
            return await call_next(request)

        if scope["method"] not in ("POST", "PUT"):
            return await call_next(request)

        if scope["path"] in self.upload_paths:
            headers = request.headers
            content_type = headers.get("content-type")

            unsupported_media_type = self.__check_content_type(content_type)

            if unsupported_media_type:
                return unsupported_media_type

            if "content-length" not in headers:
                return self.__length_required()

            content_length = headers["content-length"]

            if not search(r"^[0-9]+$", content_length):
                return self.__length_required()

            if int(content_length) > self.max_size:
                return self.__request_entity_too_large()

        return await call_next(request)

    def __check_content_type(
        self,
        current_content_type: str | None,
    ) -> JSONResponse | None:
        if current_content_type is None:
            return self.__missing_header("content-type")

        for content_type in self.SUPPORTED_TYPES:
            if search(content_type, current_content_type):
                break
        else:
            return self.__unsupported_media_type(current_content_type)

    def __missing_header(self, header: str) -> JSONResponse:
        return self._handler.exc_to_json(
            ValidationError(f"Missing header `{header}`"),
        )

    def __length_required(self) -> JSONResponse:
        return self._handler.exc_to_json(
            ValidationError(
                "Length required",
                status.HTTP_411_LENGTH_REQUIRED,
            ),
        )

    def __unsupported_media_type(self, content_type: str) -> JSONResponse:
        return self._handler.exc_to_json(
            ValidationError(
                f"Unsupported media type: {content_type}",
                status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            ),
        )

    def __request_entity_too_large(self) -> JSONResponse:
        return self._handler.exc_to_json(
            ValidationError(
                f"Media more than `{self.max_size}` bytes",
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            ),
        )
