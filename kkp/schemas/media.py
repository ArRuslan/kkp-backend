from pydantic import BaseModel

from kkp.models import MediaType


class CreateMediaUploadRequest(BaseModel):
    type: MediaType
    size: int


class CreateMediaUploadResponse(BaseModel):
    id: int
    upload_url: str


class MediaInfo(BaseModel):
    id: int
    uploaded_at: int
    type: MediaType
    photo_url: str | None
    video_url: str | None
