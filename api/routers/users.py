from typing import Annotated, Dict

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from controllers import UserController
from controllers.authenticate import APIKeyQuery
from models.managers import get_session
from models.models import BaseResultModel, ResultDetailUserModel, UserResponsesModel

router: APIRouter = APIRouter(prefix="/users")


@router.get(
    "/me",
    dependencies=[Depends(APIKeyQuery())],
    response_model=ResultDetailUserModel,
    status_code=status.HTTP_200_OK,
    responses=UserResponsesModel().me_detail_responses,
)
async def me_detail(request: Request) -> Dict:
    user_controller = UserController()

    return {"user": user_controller.user_to_dict(request.user)}


@router.get(
    "/{user_id:int}",
    response_model=ResultDetailUserModel,
    status_code=status.HTTP_200_OK,
    responses=UserResponsesModel().user_detail_responses,
)
async def user_detail(
    async_session: Annotated[AsyncSession, Depends(get_session)],
    user_id: Annotated[int, Path(..., ge=1)],
) -> Dict:
    user_controller = UserController()

    user = await user_controller.user_detail(async_session, user_id)
    return {"user": user_controller.user_to_dict(user)}


@router.post(
    "/{user_id:int}/follow",
    dependencies=[Depends(APIKeyQuery())],
    response_model=BaseResultModel,
    status_code=status.HTTP_201_CREATED,
    responses=UserResponsesModel().follow_user_responses,
)
async def follow_user(
    async_session: Annotated[AsyncSession, Depends(get_session)],
    request: Request,
    user_id: Annotated[int, Path(..., ge=1)],
) -> Dict:
    user_controller = UserController()

    await user_controller.add_follow_user(async_session, request.user, user_id)
    return {}


@router.delete(
    "/{user_id:int}/follow",
    dependencies=[Depends(APIKeyQuery())],
    response_model=BaseResultModel,
    status_code=status.HTTP_200_OK,
    responses=UserResponsesModel().unfollow_user_responses,
)
async def unfollow_user(
    async_session: Annotated[AsyncSession, Depends(get_session)],
    request: Request,
    user_id: Annotated[int, Path(..., ge=1)],
) -> Dict:
    user_controller = UserController()

    await user_controller.delete_follow_user(async_session, request.user, user_id)
    return {}
