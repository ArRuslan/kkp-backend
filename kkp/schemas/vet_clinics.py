from pydantic import BaseModel

from kkp.schemas.common import GeoPointInfo
from kkp.schemas.users import UserBaseInfo


class VetClinicInfo(BaseModel):
    id: int
    name: str
    location: GeoPointInfo
    admin: UserBaseInfo | None
    employees_count: int
