from pydantic import BaseModel

from kkp.models import AnimalStatus
from kkp.schemas.common import PaginationResponse, GeoPoint
from kkp.schemas.media import MediaInfo


class AnimalInfo(BaseModel):
    id: int
    name: str
    breed: str
    status: AnimalStatus
    description: str
    media: PaginationResponse[MediaInfo]
    current_location: GeoPoint | None
    updated_at: int


class CreateAnimalRequest(BaseModel):
    name: str
    breed: str
    status: AnimalStatus
    description: str
    media_ids: list[int]
    current_location: GeoPoint | None


class EditAnimalRequest(BaseModel):
    name: str | None = None
    breed: str | None = None
    status: AnimalStatus | None = None
    description: str | None = None
    media_ids: list[int] | None = None
    current_location: GeoPoint | None = None
