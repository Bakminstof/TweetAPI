from typing import Dict

from fastapi import status


class APIException(Exception):
    def __init__(
        self,
        detail: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        headers: Dict | None = None,
    ) -> None:
        self.detail = detail
        self.status_code = status_code
        self.type = self.__class__.__name__

        self.headers = self.__set_headers(headers)

    def __set_headers(self, headers: Dict | None) -> Dict:
        current_headers = {
            "API-Error": f"{self.type}",
            "content-type": "application/json",
        }

        if headers:
            current_headers.update(headers)

        return current_headers

    @property
    def content(self) -> Dict:
        return {"result": False, "error_type": self.type, "error_message": self.detail}


class NotFoundError(APIException):
    def __init__(
        self,
        detail: str,
        headers: Dict | None = None,
    ) -> None:
        super().__init__(
            detail=detail,
            status_code=status.HTTP_404_NOT_FOUND,
            headers=headers,
        )


class ValidationError(APIException):
    def __init__(
        self,
        detail: str,
        status_code: int = status.HTTP_422_UNPROCESSABLE_ENTITY,
        headers: Dict | None = None,
    ) -> None:
        super().__init__(
            detail=detail,
            status_code=status_code,
            headers=headers,
        )


class AuthenticationError(APIException):
    def __init__(
        self,
        detail: str,
        status_code: int = status.HTTP_401_UNAUTHORIZED,
        headers: Dict | None = None,
    ) -> None:
        super().__init__(
            detail=detail,
            status_code=status_code,
            headers=headers,
        )
