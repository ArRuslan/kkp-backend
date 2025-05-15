from pydantic import BaseModel, Field

from kkp.models import VolRequestStatus
from kkp.schemas.media import MediaInfo
from kkp.schemas.users import UserBaseInfo


class VolunteerRequestInfo(BaseModel):
    id: int
    user: UserBaseInfo
    created_at: int
    reviewed_at: int
    text: str
    review_text: str
    medias: list[MediaInfo]
    status: VolRequestStatus


class CreateVolunteerRequest(BaseModel):
    text: str
    media_ids: list[int] = Field(max_length=15)
