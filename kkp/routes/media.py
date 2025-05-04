from datetime import datetime
from time import time

from fastapi import APIRouter
from pytz import UTC

from kkp.config import config, S3
from kkp.dependencies import JwtAuthUserDep
from kkp.models import Media, MediaType, MediaStatus
from kkp.schemas.media import MediaInfo, CreateMediaUploadResponse, CreateMediaUploadRequest
from kkp.utils.custom_exception import CustomMessageException

router = APIRouter(prefix="/media")


@router.post("", response_model=CreateMediaUploadResponse)
async def create_upload(user: JwtAuthUserDep, data: CreateMediaUploadRequest):
    if (data.type is MediaType.PHOTO and data.size > config.max_photo_size) \
            or (data.type is MediaType.VIDEO and data.size > config.max_video_size):
        raise CustomMessageException(f"Maximum file size is exceeded!")

    res = await Media.create(uploaded_by=user, type=data.type)
    return {
        "id": res.id,
        "upload_url": res.upload_url(),
    }


@router.post("/{media_id}/finalize", response_model=MediaInfo)
async def finalize_upload(user: JwtAuthUserDep, media_id: int):
    if (media := await Media.get_or_none(uploaded_by=user, id=media_id)) is None:
        raise CustomMessageException(f"Unknown media!")
    if media.status is not MediaStatus.CREATED:
        raise CustomMessageException(f"Invalid media state!")
    if (time() - media.uploaded_at.timestamp()) > 60 * 60:
        await S3.delete_object(config.s3_bucket_name, media.object_key())
        await media.delete()
        raise CustomMessageException(f"Upload time exceeded!")
    if not await S3.get_object(config.s3_bucket_name, media.object_key()):
        raise CustomMessageException(f"Media is not uploaded!")

    # TODO: validate that file is indeed photo/video?

    media.uploaded_at = datetime.now(UTC)
    media.status = MediaStatus.UPLOADED
    await media.save(update_fields=["uploaded_at", "status"])

    return media.to_json()
