from pydantic import BaseModel

from kkp.schemas.animals import AnimalInfo
from kkp.schemas.common import GeoPointInfo
from kkp.schemas.media import MediaInfo
from kkp.schemas.users import UserBaseInfo


class CreateAnimalReportsRequest(BaseModel):
    # TODO: accept existing animal id if user found animal with qr code

    name: str
    breed: str
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
