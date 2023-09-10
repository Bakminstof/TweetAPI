from typing import Annotated, Dict, List

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from controllers import LikeController, TweetController
from controllers.authenticate import APIKeyHeader
from models.managers import get_session
from models.models import (
    BaseResultModel,
    CrateTweetModel,
    ResultMultipleTweetModel,
    ResultSingleTweetModel,
    TweetResponsesModel,
)

router: APIRouter = APIRouter(prefix="/tweets")


@router.get(
    "",
    dependencies=[Depends(APIKeyHeader())],
    response_model=ResultMultipleTweetModel,
    status_code=status.HTTP_200_OK,
    responses=TweetResponsesModel().get_tweet_responses,
)
async def get_tweets(
    async_session: Annotated[AsyncSession, Depends(get_session)],
) -> Dict[str, List[Dict]]:
    tweet_controller: TweetController = TweetController()

    return {"tweets": await tweet_controller.get_tweets(async_session, as_dict=True)}


@router.post(
    "",
    dependencies=[Depends(APIKeyHeader())],
    response_model=ResultSingleTweetModel,
    status_code=status.HTTP_201_CREATED,
    responses=TweetResponsesModel().create_tweet_responses,
)
async def create_tweet(
    async_session: Annotated[AsyncSession, Depends(get_session)],
    request: Request,
    twt: CrateTweetModel,
) -> Dict[str, int]:
    tweet_controller: TweetController = TweetController()

    tweet = await tweet_controller.create_tweet(twt, request.user, async_session)
    return {"tweet_id": tweet.id}


@router.delete(
    "/{tweet_id:int}",
    dependencies=[Depends(APIKeyHeader())],
    response_model=BaseResultModel,
    status_code=status.HTTP_200_OK,
    responses=TweetResponsesModel().delete_tweet_responses,
)
async def delete_tweet(
    async_session: Annotated[AsyncSession, Depends(get_session)],
    request: Request,
    tweet_id: Annotated[int, Path(..., ge=1)],
) -> Dict:
    tweet_controller: TweetController = TweetController()

    await tweet_controller.delete_tweet(tweet_id, request.user, async_session)
    return {}


@router.post(
    "/{tweet_id:int}/likes",
    dependencies=[Depends(APIKeyHeader())],
    response_model=BaseResultModel,
    status_code=status.HTTP_201_CREATED,
    responses=TweetResponsesModel().like_tweet_responses,
)
async def like_tweet(
    async_session: Annotated[AsyncSession, Depends(get_session)],
    request: Request,
    tweet_id: int,
) -> Dict:
    like_controller: LikeController = LikeController()

    await like_controller.add_like(tweet_id, request.user.id, async_session)
    return {}


@router.delete(
    "/{tweet_id:int}/likes",
    dependencies=[Depends(APIKeyHeader())],
    response_model=BaseResultModel,
    status_code=status.HTTP_200_OK,
    responses=TweetResponsesModel().dislike_tweet_responses,
)
async def dislike_tweet(
    async_session: Annotated[AsyncSession, Depends(get_session)],
    request: Request,
    tweet_id: Annotated[int, Path(..., ge=1)],
) -> Dict:
    like_controller: LikeController = LikeController()

    await like_controller.delete_like(tweet_id, request.user.id, async_session)
    return {}
