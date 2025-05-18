from typing import Literal

from pydantic import BaseModel, EmailStr

from kkp.models import UserRole
from kkp.schemas.common import PaginationQuery


class AdminEditUserRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    photo_id: int | None = None
    disable_mfa: bool | None = None


class UsersQuery(PaginationQuery):
    order: Literal["asc", "desc"] = "asc"
    order_by: Literal["id"] = "id"
    id: int | None = None
    role: UserRole | None = None
    has_mfa: bool | None = None
