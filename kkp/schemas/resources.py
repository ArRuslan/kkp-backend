from pydantic import BaseModel

from kkp.models.photo_video import ResourceType


class CreateResourceUploadRequest(BaseModel):
    type: ResourceType
    size: int


class CreateResourceUploadResponse(BaseModel):
    id: int
    upload_url: str


class PhotoVideoResource(BaseModel):
    id: int
    uploaded_at: int
    type: ResourceType
    photo_url: str | None
    video_url: str | None
