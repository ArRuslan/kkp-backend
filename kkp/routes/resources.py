from datetime import datetime
from time import time

from fastapi import APIRouter
from pytz import UTC

from kkp.config import config, S3
from kkp.dependencies import JwtAuthUserDep
from kkp.models import PhotoVideo
from kkp.models.photo_video import ResourceType, ResourceStatus
from kkp.schemas.resources import CreateResourceUploadRequest, CreateResourceUploadResponse, PhotoVideoResource
from kkp.utils.custom_exception import CustomMessageException

router = APIRouter(prefix="/resources")


@router.post("", response_model=CreateResourceUploadResponse)
async def create_upload(user: JwtAuthUserDep, data: CreateResourceUploadRequest):
    if (data.type is ResourceType.PHOTO and data.size > config.max_photo_size) \
            or (data.type is ResourceType.VIDEO and data.size > config.max_video_size):
        raise CustomMessageException(f"Maximum file size is exceeded!")

    res = await PhotoVideo.create(uploaded_by=user, type=data.type)
    return {
        "id": res.id,
        "upload_url": res.upload_url(),
    }


@router.post("/{resource_id}/finalize", response_model=PhotoVideoResource)
async def finalize_upload(user: JwtAuthUserDep, resource_id: int):
    if (resource := await PhotoVideo.get_or_none(uploaded_by=user, id=resource_id)) is None:
        raise CustomMessageException(f"Unknown resource!")
    if resource.status is not ResourceStatus.CREATED:
        raise CustomMessageException(f"Invalid resource state!")
    if (time() - resource.uploaded_at.timestamp()) > 60 * 60:
        await S3.delete_object(config.s3_bucket_name, resource.object_key())
        await resource.delete()
        raise CustomMessageException(f"Upload time exceeded!")
    if not await S3.get_object(config.s3_bucket_name, resource.object_key()):
        raise CustomMessageException(f"Resource is not uploaded!")

    # TODO: validate that file is indeed photo/video?

    resource.uploaded_at = datetime.now(UTC)
    resource.status = ResourceStatus.UPLOADED
    await resource.save(update_fields=["uploaded_at", "status"])

    return resource.to_json()
