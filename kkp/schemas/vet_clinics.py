from pydantic import BaseModel

from kkp.schemas.common import GeoPointInfo, PaginationQuery
from kkp.schemas.users import UserBaseInfo


class VetClinicInfo(BaseModel):
    id: int
    name: str
    location: GeoPointInfo
    admin: UserBaseInfo | None
    employees_count: int


class NearVetClinicsQuery(PaginationQuery):
    lat: float
    lon: float
    radius: int = 5000
