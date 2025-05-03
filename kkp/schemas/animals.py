from pydantic import BaseModel

from kkp.models import AnimalStatus
from kkp.schemas.common import PaginationResponse, GeoPoint
from kkp.schemas.resources import PhotoVideoResource


class AnimalInfo(BaseModel):
    id: int
    name: str
    breed: str
    status: AnimalStatus
    description: str
    resources: PaginationResponse[PhotoVideoResource]
    current_location: GeoPoint | None


class CreateAnimalRequest(BaseModel):
    name: str
    breed: str
    status: AnimalStatus
    description: str
    resource_ids: list[int]
    current_location: GeoPoint | None


class EditAnimalRequest(BaseModel):
    name: str | None = None
    breed: str | None = None
    status: AnimalStatus | None = None
    description: str | None = None
    resource_ids: list[int] | None = None
    current_location: GeoPoint | None = None
