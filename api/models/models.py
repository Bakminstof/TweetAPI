from typing import Any, Dict, List, Tuple

from pydantic import BaseModel, ConfigDict, Field
from starlette import status

from exceptions import APIException, AuthenticationError, NotFoundError, ValidationError


# Users
class BaseUserModel(BaseModel):
    name: str


class UserModel(BaseUserModel):
    id: int


class LikerModel(BaseUserModel):
    user_id: int


class BaseResultModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    result: bool = True


class DetailUserModel(BaseUserModel):
    id: int
    followers: List[UserModel] = []
    following: List[UserModel] = []


class ResultDetailUserModel(BaseResultModel):
    user: DetailUserModel


class ResultUserModel(BaseResultModel):
    user_id: int


# Tweets
class CrateTweetModel(BaseModel):
    tweet_data: str
    tweet_media_ids: List[int] = []


class ResultSingleTweetModel(BaseResultModel):
    tweet_id: int


class TweetItemModel(BaseModel):
    id: int
    content: str = ""
    attachments: List[str] = Field(..., title="List of media")
    author: UserModel
    likes: List[LikerModel] = []


class ResultMultipleTweetModel(BaseResultModel):
    tweets: List[TweetItemModel] = []


# Media
class ResultMediaModel(BaseResultModel):
    media_id: int


# Exceptions
class APIExceptionModel(BaseModel):
    result: bool = False
    error_type: str
    error_message: str


# Responses
class BaseResponse:
    HTTP_401_UNAUTHORIZED: Dict[str, Any] = {
        "model": APIExceptionModel,
        "description": "Invalid or missing api-key",
        "content": {
            "application/json": {
                "example": AuthenticationError("Invalid api-key").content,
            },
        },
    }
    HTTP_405_METHOD_NOT_ALLOWED: Dict[str, Any] = {
        "model": APIExceptionModel,
        "description": "Method Not Allowed",
        "content": {
            "application/json": {
                "example": AuthenticationError(
                    "Method Not Allowed",
                    status.HTTP_405_METHOD_NOT_ALLOWED,
                ).content,
            },
        },
    }
    HTTP_422_UNPROCESSABLE_ENTITY: Dict[str, Any] = {
        "model": APIExceptionModel,
        "description": "Validation Error",
        "content": {
            "application/json": {
                "example": ValidationError("Validation Error").content,
            },
        },
    }
    HTTP_500_INTERNAL_SERVER_ERROR: Dict[str, Any] = {
        "model": APIExceptionModel,
        "description": "Internal Server Error",
        "content": {
            "application/json": {
                "example": APIException(
                    "Internal Server Error",
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                ).content,
            },
        },
    }

    RESPONSES: Dict[int, Dict[str, Any]] = {
        status.HTTP_401_UNAUTHORIZED: HTTP_401_UNAUTHORIZED,
        status.HTTP_405_METHOD_NOT_ALLOWED: HTTP_405_METHOD_NOT_ALLOWED,
        status.HTTP_422_UNPROCESSABLE_ENTITY: HTTP_422_UNPROCESSABLE_ENTITY,
        status.HTTP_500_INTERNAL_SERVER_ERROR: HTTP_500_INTERNAL_SERVER_ERROR,
    }

    @classmethod
    def all(cls) -> Dict[int, Dict[str, Any]]:
        return cls.RESPONSES

    @classmethod
    def some(
        cls,
        only: List[int] | Tuple[int, ...] | None = None,
        exclude: List[int] | Tuple[int, ...] | None = None,
    ) -> Dict[int, Dict[str, Any]]:
        responses = {}

        for status_code, response in cls.RESPONSES.items():
            if only:
                if status_code in only:
                    responses[status_code] = response
                continue

            if exclude:
                if status_code not in exclude:
                    responses[status_code] = response
                continue

            responses[status_code] = response

        return responses


class UserResponsesModel(BaseModel):
    me_detail_responses: Dict[str, Any] = {
        **BaseResponse.some(exclude=[422]),
        status.HTTP_200_OK: {
            "model": ResultDetailUserModel,
            "description": "Successful Response",
        },
    }

    user_detail_responses: Dict[str, Any] = {
        **BaseResponse.some(exclude=[401, 422]),
        status.HTTP_200_OK: {
            "model": ResultDetailUserModel,
            "description": "Successful Response",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": APIExceptionModel,
            "description": "Not Found Error",
            "content": {
                "application/json": {
                    "example": APIException(
                        "It's your user ID `3`",
                    ).content,
                },
            },
        },
        status.HTTP_404_NOT_FOUND: {
            "model": APIExceptionModel,
            "description": "Not Found Error",
            "content": {
                "application/json": {
                    "example": NotFoundError(
                        "User with ID `3` not found",
                    ).content,
                },
            },
        },
    }

    follow_user_responses: Dict[str, Any] = {
        **BaseResponse.some(exclude=[422]),
        status.HTTP_201_CREATED: {
            "model": BaseResultModel,
            "description": "Successful Response",
        },
    }

    unfollow_user_responses: Dict[str, Any] = {
        **BaseResponse.some(exclude=[422]),
        status.HTTP_200_OK: {
            "model": BaseResultModel,
            "description": "Successful Response",
        },
    }


class TweetResponsesModel(BaseModel):
    get_tweet_responses: Dict[str, Any] = {
        **BaseResponse.some(exclude=[422]),
        status.HTTP_200_OK: {
            "model": ResultMultipleTweetModel,
            "description": "Successful Response",
        },
    }

    create_tweet_responses: Dict[str, Any] = {
        **BaseResponse.all(),
        status.HTTP_201_CREATED: {
            "model": ResultSingleTweetModel,
            "description": "Successful Response",
        },
    }

    delete_tweet_responses: Dict[str, Any] = {
        **BaseResponse.some(exclude=[422]),
        status.HTTP_200_OK: {
            "model": BaseResultModel,
            "description": "Successful Response",
        },
    }

    like_tweet_responses: Dict[str, Any] = {
        **BaseResponse.some(exclude=[422]),
        status.HTTP_201_CREATED: {
            "model": BaseResultModel,
            "description": "Successful Response",
        },
    }

    dislike_tweet_responses: Dict[str, Any] = {
        **BaseResponse.some(exclude=[422]),
        status.HTTP_200_OK: {
            "model": BaseResultModel,
            "description": "Successful Response",
        },
    }


class MediaResponsesModel(BaseModel):
    upload_media_responses: Dict[str, Any] = {
        **BaseResponse.all(),
        status.HTTP_201_CREATED: {
            "model": ResultMediaModel,
            "description": "Loaded media",
        },
        status.HTTP_411_LENGTH_REQUIRED: {
            "model": APIExceptionModel,
            "description": "Length required",
            "content": {
                "application/json": {
                    "example": ValidationError(
                        "Length required",
                        status.HTTP_411_LENGTH_REQUIRED,
                    ).content,
                },
            },
        },
        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: {
            "model": APIExceptionModel,
            "description": "Media more than `size` MB",
            "content": {
                "application/json": {
                    "example": ValidationError(
                        "Media more than `6` MB",
                        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    ).content,
                },
            },
        },
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: {
            "model": APIExceptionModel,
            "description": "Unsupported media type: `input_media_type`",
            "content": {
                "application/json": {
                    "example": ValidationError(
                        "Unsupported media type: `audio/mpeg`",
                        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    ).content,
                },
            },
        },
    }
