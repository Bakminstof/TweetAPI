from typing import Callable, Type

from fastapi import FastAPI, HTTPException, status
from fastapi.exceptions import RequestValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse

from .exceptions import APIException, AuthenticationError, NotFoundError, ValidationError


class ExceptionHandler:
    @staticmethod
    def exc_to_json(
        exception: APIException,
    ) -> JSONResponse:
        return JSONResponse(
            content=exception.content,
            status_code=exception.status_code,
            headers=exception.headers,
        )

    async def handler_api_exc(
        self,
        request: Request,
        exception,
    ) -> JSONResponse:
        return self.exc_to_json(exception)

    async def handler_404(
        self,
        request: Request,
        exception: HTTPException,
    ) -> JSONResponse:
        return self.exc_to_json(NotFoundError(exception.detail))

    async def handler_405(
        self,
        request: Request,
        exception: HTTPException,
    ) -> JSONResponse:
        return self.exc_to_json(
            APIException(
                exception.detail,
                status.HTTP_405_METHOD_NOT_ALLOWED,
            ),
        )

    async def handler_422(
        self,
        request: Request,
        exception: RequestValidationError,
    ) -> JSONResponse:
        exc_mess_list = []

        for exc in exception.errors():
            exc_mess_list.append(f"{exc['msg']}. Location: {exc['loc']}")

        exc_mess = " |\n".join(exc_mess_list)

        return self.exc_to_json(ValidationError(exc_mess))

    async def handler_500(
        self,
        request: Request,
        exception: HTTPException,
    ) -> JSONResponse:
        return self.exc_to_json(
            APIException(
                exception.detail,
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ),
        )


class ExceptionRegistrator:
    _handler: ExceptionHandler | None = None
    _app: FastAPI | None = None

    def __init__(self, app: FastAPI) -> None:
        self._app = app
        self._handler = ExceptionHandler()

    def register(
        self,
        exc_class_or_status_code: int | Type[Exception],
        handler: Callable,
    ) -> None:
        self._app.add_exception_handler(exc_class_or_status_code, handler)

    def register_all(self) -> None:
        # 400, APIException
        self.register(APIException, self._handler.handler_api_exc)

        # 401, 403, AuthenticationError
        self.register(AuthenticationError, self._handler.handler_api_exc)

        # 404, NotFoundError
        self.register(NotFoundError, self._handler.handler_api_exc)
        self.register(status.HTTP_404_NOT_FOUND, self._handler.handler_404)

        # 405
        self.register(
            status.HTTP_405_METHOD_NOT_ALLOWED,
            self._handler.handler_405,
        )

        # 422, RequestValidationError, ValidationError
        self.register(RequestValidationError, self._handler.handler_422)
        self.register(ValidationError, self._handler.handler_api_exc)

        # 500
        self.register(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            ExceptionHandler.handler_500,
        )
