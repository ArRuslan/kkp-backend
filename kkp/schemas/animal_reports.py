from pydantic import BaseModel

from kkp.schemas.animals import AnimalInfo
from kkp.schemas.common import GeoPointInfo, PaginationQuery
from kkp.schemas.media import MediaInfo
from kkp.schemas.users import UserBaseInfo


class CreateAnimalReportsRequest(BaseModel):
    animal_id: int | None = None

    name: str | None = None
    breed: str | None = None
    notes: str
    latitude: float
    longitude: float
    media_ids: list[int]


class AnimalReportInfo(BaseModel):
    id: int
    reported_by: UserBaseInfo | None
    animal: AnimalInfo
    created_at: int
    assigned_to: UserBaseInfo | None
    notes: str
    media: list[MediaInfo]
    location: GeoPointInfo


class RecentReportsQuery(PaginationQuery):
    lat: float
    lon: float
    radius: int = 5000
