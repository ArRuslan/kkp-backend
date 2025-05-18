from typing import Literal

from pydantic import BaseModel

from kkp.models import VolRequestStatus
from kkp.schemas.common import PaginationQuery


class VolReqPaginationQuery(PaginationQuery):
    order: Literal["asc", "desc"] = "asc"
    order_by: Literal["id", "status", "created_at", "reviewed_at"] = "id"
    status: VolRequestStatus = VolRequestStatus.REQUESTED
    id: int | None = None
    user_id: int | None = None


class ApproveRejectVolunteerRequest(BaseModel):
    text: str
