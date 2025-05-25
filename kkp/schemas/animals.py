from pydantic import BaseModel

from kkp.models import AnimalStatus
from kkp.schemas.common import PaginationResponse, GeoPointInfo
from kkp.schemas.media import MediaInfo


class AnimalInfo(BaseModel):
    id: int
    name: str
    breed: str
    status: AnimalStatus
    description: str
    media: PaginationResponse[MediaInfo]
    current_location: GeoPointInfo | None
    updated_at: int
    # `subscribed` field is only returned in /subscriptions, /animals and /animals/{animal_id} routes
    subscribed: bool


class CreateAnimalRequest(BaseModel):
    name: str
    breed: str
    status: AnimalStatus
    description: str
    media_ids: list[int]
    current_location: GeoPointInfo | None


class EditAnimalRequest(BaseModel):
    name: str | None = None
    breed: str | None = None
    status: AnimalStatus | None = None
    description: str | None = None
    add_media_ids: list[int] | None = None
    remove_media_ids: list[int] | None = None
    current_latitude: float | None = None
    current_longitude: float | None = None
