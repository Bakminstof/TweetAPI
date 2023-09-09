from asyncio import Task
from threading import Thread
from typing import Any, AsyncGenerator, Dict, List, Tuple, Type
from urllib.parse import quote_plus
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import URL
from sqlalchemy.ext.asyncio import AsyncSession

from alembic.command import upgrade
from controllers import MediaController
from main import app as app_for_tests
from models.managers import (
    DatabaseAsyncSessionManager,
    MediaManager,
    TweetManager,
    db_session_manager,
)
from models.mixins import CRUDMixin
from models.models import CrateTweetModel
from models.schemas import Media, Token, Tweet, TweetMedia, User
from settings import settings
from tests.db_utils import DBManager, alembic_config_from_url
from tests.test_media import MediaItem

MIGRATION_TASK: Task | None = None


# Utils
async def __clear_table(table: Type[Any], async_session: AsyncSession) -> None:
    mixin = CRUDMixin()
    mixin.table = table
    await mixin.delete(async_session)

    print(f"Clear {mixin.table.__name__} table")


# Session scope
@pytest.fixture(scope="session", name="anyio_backend", autouse=True)
def anyio_backend() -> Tuple[str, Dict[str, bool]]:
    print("Set anyio_backend")
    return "asyncio", {"use_uvloop": True}


@pytest.fixture(scope="session", name="threads", autouse=True)
def threads() -> None:
    MediaController.start_threads()
    yield
    MediaController.stop_threads()


@pytest.fixture(scope="session", name="pg_url")
def pg_url() -> URL:
    """Provides base PostgreSQL URL for creating temporary databases."""
    return settings.DB_URL


@pytest.fixture(scope="session", name="migrated_postgres_template")
async def migrated_postgres_template(pg_url: URL) -> URL:
    """
    Creates temporary database and applies migrations.
    """
    async with DBManager().create_tmp_database(pg_url, "pytest") as tmp_url:
        settings.DB_URL = tmp_url

        password = quote_plus(tmp_url.password).replace("%", "%%")
        tmp_url_for_alembic = URL.create(
            drivername=tmp_url.drivername,
            username=tmp_url.username,
            password=password,
            host=tmp_url.host,
            port=tmp_url.port,
            database=tmp_url.database,
        )

        alembic_config = alembic_config_from_url(
            tmp_url_for_alembic.render_as_string(False),
        )

        upgrade(alembic_config, "head")

        if MIGRATION_TASK:
            await MIGRATION_TASK

        yield tmp_url


@pytest.fixture(scope="session", name="sessionmanager_for_tests")
async def sessionmanager_for_tests(
    migrated_postgres_template: URL,
) -> DatabaseAsyncSessionManager:
    db_session_manager.init(migrated_postgres_template, echo_sql=settings.ECHO_SQL)

    yield db_session_manager
    await db_session_manager.close()


# Class scope
@pytest.fixture(scope="class", name="images_data")
def images_data() -> List[MediaItem]:
    print("Image data build start")

    test_images: List[MediaItem] = []
    workers = []

    for image_name in MediaItem.IMAGES_DIR.iterdir():
        media = MediaItem(image_name.name)
        test_images.append(media)

        thread = Thread(target=MediaItem.to_bytes, args=(media, media.file))
        thread.start()

        workers.append(thread)

    for worker in workers:
        worker.join(5)

    del workers

    print(f"Image data build complete: ({len(test_images)})")

    yield test_images
    del test_images

    print("Delete image data")


# Function scope
@pytest.fixture(name="app")
def app() -> FastAPI:
    yield app_for_tests


@pytest.fixture(name="client")
async def client(session: AsyncSession, app: FastAPI) -> AsyncClient:
    async with AsyncClient(app=app, base_url="http://test") as test_client:
        yield test_client


@pytest.fixture(name="session")
async def session(
    sessionmanager_for_tests: DatabaseAsyncSessionManager,
) -> AsyncGenerator[AsyncSession, None]:
    async with sessionmanager_for_tests.session() as ses:
        yield ses


@pytest.fixture(name="users")
async def users(session: AsyncSession) -> List[User]:
    usernames = [f"TestUser[{uuid4().hex}]" for _ in range(10)]

    test_users = await DBManager.create_test_users(usernames, session)
    print("Create users")

    await DBManager.create_test_tokens(test_users, session)
    print("Create tokens")

    yield test_users

    for table in [Media, TweetMedia, Tweet, Token, User]:
        await __clear_table(table, session)


@pytest.fixture(name="media")
async def media(session: AsyncSession) -> List[Media]:
    media_manager = MediaManager()

    test_media = []

    for i in range(10):
        name = f"TestMedia[{i + 1}]"
        path = f"/test/media/path/{i + 1}"

        media = Media(name=name, file=path)
        await media_manager.add(session, media)
        test_media.append(media)

    yield test_media

    await __clear_table(Media, session)


@pytest.fixture(name="tweets")
async def tweets(
    session: AsyncSession,
    users: List[User],
    media: List[Media],
) -> List[Tweet]:
    test_tweets = []

    tweet_manager = TweetManager()

    for user, media_item in zip(users, media):
        tweet_model = CrateTweetModel(
            tweet_data=f"TestTweetContent[{media_item.id}]",
            tweet_media_ids=[media_item.id],
        )

        tweet_media = TweetMedia()
        tweet_media.media_item = media_item

        session.add(tweet_media)

        tweet = Tweet(
            author_id=user.id,
            author=user,
            content=tweet_model.tweet_data,
            likers=[],
        )
        tweet.attachments.append(tweet_media)

        test_tweets.append(tweet)

    test_tweets = await tweet_manager.add_all(session, test_tweets)

    print(f"Create tweets: [{test_tweets}]")

    yield test_tweets

    for table in [Media, TweetMedia, Tweet]:
        await __clear_table(table, session)
