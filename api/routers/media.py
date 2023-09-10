from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import FormData
from starlette.requests import Request

from controllers import MediaController
from controllers.authenticate import APIKeyHeader
from models.managers import get_session
from models.models import MediaResponsesModel, ResultMediaModel

router = APIRouter(prefix="/medias")


@router.post(
    "",
    name="upload_media",
    dependencies=[Depends(APIKeyHeader())],
    response_model=ResultMediaModel,
    status_code=status.HTTP_201_CREATED,
    description="Form-data is expected",
    responses=MediaResponsesModel().upload_media_responses,
)
async def upload_media(
    async_session: Annotated[AsyncSession, Depends(get_session)],
    request: Request,
) -> ResultMediaModel:
    media_controller = MediaController()

    form: FormData = await request.form()
    media = await media_controller.save_media(form, async_session)

    data = ResultMediaModel(media_id=media[0].id)
    return ResultMediaModel.model_validate(data)
