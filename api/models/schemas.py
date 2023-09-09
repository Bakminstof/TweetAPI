from __future__ import annotations

from typing import Any, Dict, List, Tuple

from sqlalchemy import ForeignKey, ForeignKeyConstraint, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import BIGINT, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    def to_dict(
        self,
        only: List[str] | Tuple[str, ...] | None = None,
        exclude: List[str] | Tuple[str, ...] | None = None,
    ) -> Dict[str, Any]:
        item = {}

        for column in self.__table__.columns:  # noqa
            if column.key in self.__dict__:
                if only:
                    if column.key in only:
                        item[column.key] = getattr(self, column.key)
                    continue

                if exclude:
                    if column.key not in exclude:
                        item[column.key] = getattr(self, column.key)
                    continue

                item[column.key] = getattr(self, column.key)

        return item


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        "id",
        BIGINT,
        autoincrement=True,
        nullable=False,
        unique=True,
        primary_key=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        "name",
        String(200),
        nullable=False,
        index=True,
        unique=True,
    )
    followers: Mapped[JSON] = mapped_column(
        "followers",
        JSON,
        default=lambda: {},
    )
    following: Mapped[JSON] = mapped_column(
        "following",
        JSON,
        default=lambda: {},
    )

    # Tweets relationship
    tweets: Mapped[List[Tweet]] = relationship(
        lambda: Tweet,
        uselist=True,
        back_populates="author",
        lazy="joined",
        cascade="save-update, merge",
    )

    # Likes relationship
    tweets_likes: Mapped[List[Like]] = relationship(
        uselist=True,
        back_populates="liker",
        lazy="joined",
        cascade="delete",
    )

    # Token relationship
    token: Mapped[Token] = relationship(
        lambda: Token,
        back_populates="user",
        lazy="joined",
        single_parent=True,
        cascade="delete, delete-orphan",
    )


class Token(Base):
    __tablename__ = "tokens"

    id: Mapped[int] = mapped_column(
        "id",
        BIGINT,
        autoincrement=True,
        nullable=False,
        unique=True,
        primary_key=True,
        index=True,
    )
    api_key: Mapped[int] = mapped_column(
        "api_key",
        String(200),
        unique=True,
        nullable=False,
        index=True,
    )

    # User relationship
    user_id: Mapped[int] = mapped_column(
        "user_id",
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    user: Mapped[User] = relationship(
        lambda: User,
        back_populates="token",
        lazy="joined",
    )


class Like(Base):
    __tablename__ = "likes"
    __table_args__: Tuple[UniqueConstraint] = (
        UniqueConstraint(
            "user_id",
            "tweet_id",
            name="_user_tweet_uc",
        ),
    )

    id: Mapped[int] = mapped_column(
        "id",
        BIGINT,
        autoincrement=True,
        nullable=False,
        unique=True,
        primary_key=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tweet_id: Mapped[int] = mapped_column(
        ForeignKey("tweets.id", ondelete="CASCADE"),
        primary_key=True,
    )

    liker: Mapped["User"] = relationship(
        back_populates="tweets_likes",
        lazy="joined",
    )
    liked_tweet: Mapped["Tweet"] = relationship(
        back_populates="likers",
        lazy="joined",
    )


class Tweet(Base):
    __tablename__ = "tweets"

    id: Mapped[int] = mapped_column(
        "id",
        BIGINT,
        autoincrement=True,
        nullable=False,
        unique=True,
        primary_key=True,
        index=True,
    )

    content: Mapped[str] = mapped_column(
        "content",
        String(10_000),
        nullable=False,
    )

    # Author(User) relationship
    author_id: Mapped[int] = mapped_column(
        "author_id",
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
    )
    author: Mapped[User] = relationship(
        User,
        back_populates="tweets",
        lazy="joined",
    )

    # Users relationship
    likers: Mapped[List[Like]] = relationship(
        uselist=True,
        back_populates="liked_tweet",
        lazy="joined",
        cascade="delete",
    )

    # Media relationship
    attachments: Mapped[List[TweetMedia]] = relationship(
        uselist=True,
        back_populates="tweet",
        cascade="delete, delete-orphan",
        lazy="joined",
    )


class TweetMedia(Base):
    __tablename__ = "tweet_media"
    __table_args__: Tuple[ForeignKeyConstraint] = (
        UniqueConstraint(
            "media_id",
            "tweet_id",
            name="_tweet_media_uc",
        ),
    )

    id: Mapped[int] = mapped_column(
        "id",
        BIGINT,
        autoincrement=True,
        nullable=False,
        unique=True,
        primary_key=True,
    )

    tweet_id: Mapped[int] = mapped_column(
        ForeignKey("tweets.id", ondelete="CASCADE"),
        primary_key=True,
    )
    media_id: Mapped[int] = mapped_column(
        ForeignKey("media.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Media relationship
    media_item: Mapped["Media"] = relationship(
        back_populates="tweet_item",
        lazy="joined",
    )

    # Tweet relationship
    tweet: Mapped["Tweet"] = relationship(
        back_populates="attachments",
        lazy="joined",
    )


class Media(Base):
    __tablename__ = "media"

    filename_max_length: int = 20

    id: Mapped[int] = mapped_column(
        "id",
        BIGINT,
        autoincrement=True,
        nullable=False,
        unique=True,
        primary_key=True,
    )
    name: Mapped[str] = mapped_column(
        "name",
        String(filename_max_length),
        nullable=False,
    )
    file: Mapped[str] = mapped_column(
        "file",
        String(200),
        nullable=True,
    )

    # Tweet relationship
    tweet_item: Mapped[TweetMedia] = relationship(
        back_populates="media_item",
        lazy="joined",
    )
