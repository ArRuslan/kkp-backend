from pydantic import BaseModel

from kkp.schemas.common import GeoPointInfo
from kkp.schemas.users import UserBaseInfo


class CreateVetClinicRequest(BaseModel):
    name: str
    latitude: float
    longitude: float
    admin_id: int | None


class EditVetClinicRequest(BaseModel):
    name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    # Only for global admins; 0 to remove admin
    admin_id: int | None = None


class EditEmployeeRequest(BaseModel):
    email: str
