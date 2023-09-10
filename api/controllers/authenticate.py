from fastapi.security import APIKeyHeader as FastApiAPIKeyHeader
from starlette.requests import Request

from exceptions import AuthenticationError
from models.managers import UserManager, db_session_manager


class APIKeyHeader(FastApiAPIKeyHeader):
    def __init__(self, name: str = "api-key") -> None:
        super().__init__(name=name)
        self.user_manager: UserManager = UserManager()
        self.__db_session_manager = db_session_manager

    async def __call__(self, request: Request) -> str | None:
        api_key = request.headers.get(self.model.name)

        if not api_key:
            raise AuthenticationError(f"Missing `{self.model.name}` header")

        async with self.__db_session_manager.session() as async_session:
            user = await self.user_manager.get_user_by_api_key(api_key, async_session)

        if not user:
            raise AuthenticationError(f"Invalid {self.model.name}")

        request.scope["user"] = user
        return api_key
