from asyncio import sleep
from os.path import getsize
from pathlib import Path
from random import choice
from shutil import rmtree
from typing import List

from fastapi import status
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from models.managers import MediaManager
from models.schemas import Media, User
from settings import settings
from tests.common import method_not_allowed, unauthorised


class MediaItem:
    IMAGES_DIR: Path = Path(__file__).parent / "images"

    def __init__(self, name: str) -> None:
        self.name: str = name
        self.bytes: bytes | None = None

    @property
    def file(self) -> str:
        file = self.IMAGES_DIR / self.name
        return str(file.absolute().resolve())

    @property
    def size(self) -> int:
        return getsize(self.file)

    def to_bytes(self, filename: str) -> None:
        path = Path(filename)

        with path.open(mode="rb") as file:
            self.bytes = file.read()

    @classmethod
    def del_media(cls, media: Media) -> None:
        path = Path(media.file)

        if path.exists():
            rmtree(path.parent)
            print(f"Deleted: {path.parent}")
        else:
            print(f"Not exists: {path.absolute()}")


async def clear_media(session: AsyncSession, media_id: int, delay: int = 2) -> None:
    media_manager = MediaManager()

    media_items = await media_manager.get_media(session, [media_id])

    if media_items:
        await sleep(delay)
        MediaItem.del_media(media_items[0])
        await media_manager.delete(session, [Media.id == media_id])


class TestUploadMedia:
    URL = "/api/media"
    _METHOD = "POST"

    media_id: int | None = None

    async def test_valid(
        self,
        client: AsyncClient,
        images_data: List[MediaItem],
        users: List[User],
        session: AsyncSession,
    ) -> None:
        params = {"api-key": choice(users).token.api_key}

        image = choice(
            [media for media in images_data if media.size < settings.MAX_MEDIA_SIZE],
        )

        print(f"Image: {image.name}")

        files = {"file": (image.name, image.bytes)}

        response: Response = await client.request(
            method=self._METHOD,
            url=self.URL,
            files=files,
            params=params,
        )

        response_json = response.json()

        assert response.status_code == status.HTTP_201_CREATED
        assert response_json["result"] is True

        await clear_media(session, response_json["media_id"])

    async def test_empty_filename(
        self,
        client: AsyncClient,
        images_data: List[MediaItem],
        users: List[User],
    ) -> None:
        params = {"api-key": choice(users).token.api_key}

        image = choice(
            [media for media in images_data if media.size < settings.MAX_MEDIA_SIZE],
        )

        print(f"Image: {image.name}")

        files = {"file": ("", image.bytes)}

        response: Response = await client.request(
            method=self._METHOD,
            url=self.URL,
            files=files,
            params=params,
        )

        response_json = response.json()

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert response_json["result"] is False
        assert response_json["error_message"] == "File error"

    async def test_large_entity(
        self,
        client: AsyncClient,
        images_data: List[MediaItem],
        users: List[User],
    ) -> None:
        params = {"api-key": choice(users).token.api_key}

        image = choice(
            [media for media in images_data if media.size > settings.MAX_MEDIA_SIZE],
        )

        print(f"Image: {image.name}")

        files = {"file": (image.name, image.bytes)}

        response: Response = await client.request(
            method=self._METHOD,
            url=self.URL,
            files=files,
            params=params,
        )
        response_json = response.json()

        assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        assert response_json["result"] is False

    async def test_invalid_content_type(
        self,
        client: AsyncClient,
        users: List[User],
    ) -> None:
        params = {"api-key": choice(users).token.api_key}
        headers = {"content-type": ""}

        response: Response = await client.request(
            method=self._METHOD,
            url=self.URL,
            params=params,
            headers=headers,
        )

        response_json = response.json()

        assert response.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
        assert response_json["result"] is False

    async def test_invalid_content_length(
        self,
        client: AsyncClient,
        users: List[User],
    ) -> None:
        params = {"api-key": choice(users).token.api_key}
        headers = {"content-length": "", "content-type": "multipart/form-data"}

        response: Response = await client.request(
            self._METHOD,
            self.URL,
            params=params,
            headers=headers,
        )

        response_json = response.json()

        assert response.status_code == status.HTTP_411_LENGTH_REQUIRED
        assert response_json["result"] is False
        assert response_json["error_message"] == "Length required"

    async def test_empty_file(
        self,
        client: AsyncClient,
        users: List[User],
    ) -> None:
        params = {"api-key": choice(users).token.api_key}

        response: Response = await client.request(
            method=self._METHOD,
            url=self.URL,
            params=params,
        )

        response_json = response.json()

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert response_json["result"] is False

    async def test_unauthorised(
        self,
        client: AsyncClient,
    ) -> None:
        headers = {"content-type": "multipart/form-data"}

        result = await unauthorised(
            method=self._METHOD,
            url=self.URL,
            client=client,
            headers=headers,
        )
        assert result == "Missing `api-key` header"

    async def test_bad_api_key(
        self,
        client: AsyncClient,
    ) -> None:
        params = {"api-key": -1}
        headers = {"content-type": "multipart/form-data"}

        result = await unauthorised(
            method=self._METHOD,
            url=self.URL,
            client=client,
            params=params,
            headers=headers,
        )
        assert result == "Invalid api-key"

    async def test_not_allowed_method(
        self,
        client: AsyncClient,
        users: List[User],
    ) -> None:
        user = choice(users)
        params = {"api-key": user.token.api_key}
        headers = {"content-type": "multipart/form-data"}

        result = await method_not_allowed(
            not_allowed_method="PUT",
            url=self.URL,
            client=client,
            params=params,
            headers=headers,
        )
        assert result == "Method Not Allowed"
