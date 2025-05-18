from typing import Literal

from pydantic import BaseModel

from kkp.schemas.common import GeoPointInfo, PaginationQuery
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


class VetClinicsQuery(PaginationQuery):
    order: Literal["asc", "desc"] = "asc"
    order_by: Literal["id"] = "id"
    id: int | None = None
    admin_id: int | None = None
