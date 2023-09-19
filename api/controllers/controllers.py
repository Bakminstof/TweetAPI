import re
from logging import getLogger
from pathlib import Path
from queue import Queue
from threading import Event
from typing import Dict, List, Sequence
from uuid import uuid4

from fastapi import UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import FormData

from exceptions import APIException, AuthenticationError, NotFoundError, ValidationError
from models.managers import LikeManager, MediaManager, TweetManager, UserManager
from models.models import CrateTweetModel
from models.schemas import Like, Media, Tweet, TweetMedia, User
from settings import settings
from utils.threads import ReadThread, WriteThread

logger = getLogger(__name__)


class LikeController:
    def __init__(self) -> None:
        self.like_manager: LikeManager = LikeManager()
        self.tweet_manager: TweetManager = TweetManager()

    async def __check_tweet_exists(
        self,
        async_session: AsyncSession,
        tweet_id: int,
    ) -> None:
        tweet_exists = await self.tweet_manager.exists(
            async_session,
            [Tweet.id == tweet_id],
        )

        if not tweet_exists:
            raise NotFoundError(f"Tweet with id `{tweet_id}` not found")

    async def add_like(
        self,
        tweet_id: int,
        user_id: int,
        async_session: AsyncSession,
    ) -> Like:
        await self.__check_tweet_exists(async_session, tweet_id)
        like = await self.like_manager.exists(
            async_session,
            [Like.tweet_id == tweet_id, Like.user_id == user_id],
        )

        if like:
            raise APIException("Tweet already liked")

        return await self.like_manager.add(
            async_session,
            Like(user_id=user_id, tweet_id=tweet_id),
        )

    async def delete_like(
        self,
        tweet_id: int,
        user_id: int,
        async_session: AsyncSession,
    ) -> bool:
        await self.__check_tweet_exists(async_session, tweet_id)

        like = await self.like_manager.delete(
            async_session,
            [Like.tweet_id == tweet_id, Like.user_id == user_id],
        )

        if not like:
            raise APIException("This tweet not liked")

        return True


class TweetController:
    def __init__(self) -> None:
        self.tweet_manager: TweetManager = TweetManager()
        self.media_manager: MediaManager = MediaManager()

    async def get_tweets(
        self,
        async_session: AsyncSession,
        as_dict: bool = False,
    ) -> Sequence[Tweet] | List[Dict]:
        tweets = await self.tweet_manager.get_tweets(async_session)

        if as_dict:
            tweets = self._for_result_model(tweets)

        return tweets

    @staticmethod
    def _for_result_model(tweets_db: Sequence[Tweet]) -> List[Dict]:
        tweets = []

        for tweet in tweets_db:
            twt = {
                "id": tweet.id,
                "content": tweet.content,
                "attachments": [att.id for att in tweet.attachments],
                "author": {
                    "id": tweet.author.id,
                    "name": tweet.author.name,
                },
                "likes": [
                    {
                        "user_id": like.liker.id,
                        "name": like.liker.name,
                    }
                    for like in tweet.likers
                ],
            }

            tweets.append(twt)

        return tweets

    async def create_tweet(
        self,
        tweet: CrateTweetModel,
        user: User,
        async_session: AsyncSession,
    ) -> Tweet:
        attachments = []

        if tweet.tweet_media_ids:
            media = await self.media_manager.get_media(
                async_session,
                tweet.tweet_media_ids,
            )

            for media_item in media:
                attachments.append(TweetMedia(media_item=media_item))

            async_session.add_all(attachments)

        twt = Tweet(
            author=user,
            content=tweet.tweet_data,
            attachments=attachments,
        )

        return await self.tweet_manager.add(async_session, twt)

    async def delete_tweet(
        self,
        tweet_id: int,
        user: User,
        async_session: AsyncSession,
    ) -> bool:
        tweet = await self.tweet_manager.get_tweet_with_author_id(async_session, tweet_id)

        if tweet.author.id != user.id:
            raise AuthenticationError("Wrong owner", status.HTTP_403_FORBIDDEN)

        res = await self.tweet_manager.delete(async_session, [Tweet.id == tweet_id])

        if not res:
            raise NotFoundError(f"Tweet with id `{tweet_id}` not found")

        return res


class UserController:
    def __init__(self) -> None:
        self.user_manager: UserManager = UserManager()

    @staticmethod
    def user_to_dict(user: User) -> Dict:
        followers = [
            {"id": int(user_id), "name": user_name}
            for user_id, user_name in user.followers.items()
        ]
        following = [
            {"id": int(user_id), "name": user_name}
            for user_id, user_name in user.following.items()
        ]

        user_dict = user.to_dict()

        user_dict["followers"] = followers
        user_dict["following"] = following

        return user_dict

    async def user_detail(self, async_session: AsyncSession, user_id: int) -> User:
        user = await self.user_manager.get_user_detail(async_session, user_id)

        if not user:
            raise NotFoundError(f"User with ID `{user_id}` not found")

        return user

    async def __get_target_user(
        self,
        async_session: AsyncSession,
        user_id: int,
        target_user_id: int,
    ) -> User:
        if user_id == target_user_id:
            raise APIException(f"It's your user ID `{target_user_id}`")

        return await self.user_detail(async_session, target_user_id)

    async def add_follow_user(
        self,
        async_session: AsyncSession,
        user: User,
        target_user_id: int,
    ) -> None:
        target_user = await self.__get_target_user(
            async_session,
            user.id,
            target_user_id,
        )

        str_target_user_id = str(target_user_id)
        str_user_id = str(user.id)

        if str_user_id in target_user.followers:
            raise APIException(
                f"You already followed user with user_id `{target_user_id}`",
            )

        user.following[str_target_user_id] = target_user.name
        target_user.followers[str_user_id] = user.name

        await self.user_manager.update(
            async_session,
            [
                user.to_dict(),
                target_user.to_dict(),
            ],
        )

    async def delete_follow_user(
        self,
        async_session: AsyncSession,
        user: User,
        target_user_id: int,
    ) -> None:
        target_user = await self.__get_target_user(
            async_session,
            user.id,
            target_user_id,
        )

        str_target_user_id = str(target_user_id)
        str_user_id = str(user.id)

        if str_user_id not in target_user.followers:
            raise APIException(
                f"You are not followed user with user_id `{target_user_id}`",
            )

        user.following.pop(str_target_user_id)
        target_user.followers.pop(str_user_id)

        await self.user_manager.update(
            async_session,
            [
                user.to_dict(),
                target_user.to_dict(),
            ],
        )


class MediaController:
    __write_queue: Queue = Queue(100_000)
    __read_queue: Queue = Queue(10_000)
    __stop_event: Event = Event()

    __THREADS: List[ReadThread | WriteThread] = [
        ReadThread(__read_queue, __write_queue, __stop_event),
        WriteThread(__write_queue, __stop_event),
    ]

    def __init__(self) -> None:
        self.media_manager: MediaManager = MediaManager()

    @classmethod
    def start_threads(cls) -> None:
        for thread in cls.__THREADS:
            thread.start()

    @classmethod
    def stop_threads(cls) -> None:
        cls.__stop_event.set()

        for thread in cls.__THREADS:
            thread.stop()

    @staticmethod
    def __create_media_item_dir(media_item_id: int) -> Path:
        media_item_dir: Path = settings.MEDIA_DIR / str(media_item_id)

        if not media_item_dir.exists() or not media_item_dir.is_dir():
            media_item_dir.mkdir()

        return media_item_dir

    @classmethod
    def __cut_off(cls, text: str, max_length: int, join_symbol: str = "_") -> str:
        offset = 1
        cut_index = (max_length // 2) - offset

        first_half = text[:cut_index]
        middle = join_symbol * offset * 2
        second_half = text[-cut_index:]

        return f"{first_half}{middle}{second_half}"

    def __refactor_filename(self, name: str) -> str:
        max_length = self.media_manager.table.filename_max_length

        if not name:
            return uuid4().hex

        name = re.sub(r"[/\\]", "", name)  # Remove / and \

        if len(name) > max_length:
            return self.__cut_off(name, max_length)

        return name

    async def __create_media_items(
        self,
        files: List[UploadFile],
        async_session: AsyncSession,
    ) -> List[Media]:
        media = []

        for file in files:
            try:
                UploadFile.validate(file)
            except ValueError as exc:
                raise ValidationError("File error") from exc

            media.append(Media(name=self.__refactor_filename(file.filename)))

        return await self.media_manager.add_all(
            async_session,
            media,
        )

    async def __update_media_items(
        self,
        media_items: List[Media],
        async_session: AsyncSession,
    ) -> None:
        to_update = []

        for media in media_items:
            media_item_dir = self.__create_media_item_dir(media.id)
            media_location = media_item_dir / media.name
            media.file = str(media_location.absolute().resolve())
            to_update.append(media.to_dict())

        await self.media_manager.update(async_session, to_update)

    async def _save_media(
        self,
        files: List[UploadFile],
        async_session: AsyncSession,
    ) -> List[Media]:
        if self.__stop_event.is_set():
            info = "Queue is closed"
            logger.critical(info)
            raise APIException(info, status.HTTP_500_INTERNAL_SERVER_ERROR)

        media_items = await self.__create_media_items(files, async_session)
        await self.__update_media_items(media_items, async_session)

        self.__read_queue.put((media_items, files))

        return media_items

    async def save_media(
        self,
        form: FormData,
        async_session: AsyncSession,
    ) -> List[Media]:
        field_name = "file"
        files: List[UploadFile] = form.getlist(field_name)

        if not files:
            raise ValidationError(f"Empty field: `{field_name}`")

        return await self._save_media(files, async_session)
