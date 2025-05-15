from pydantic import BaseModel

from kkp.models import VolRequestStatus
from kkp.schemas.common import PaginationQuery


class VolReqPaginationQuery(PaginationQuery):
    status: VolRequestStatus = VolRequestStatus.REQUESTED


class ApproveRejectVolunteerRequest(BaseModel):
    text: str
