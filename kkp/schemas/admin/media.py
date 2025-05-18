from typing import Literal

from kkp.models import AnimalStatus, MediaType, MediaStatus
from kkp.schemas.common import PaginationQuery


class MediaQuery(PaginationQuery):
    order: Literal["asc", "desc"] = "asc"
    order_by: Literal["id", "uploaded_at"] = "id"
    id: int | None = None
    type: MediaType | None = None
    status: MediaStatus | None = None
    uploaded_by_id: int | None = None
