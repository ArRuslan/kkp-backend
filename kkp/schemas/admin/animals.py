from typing import Literal

from kkp.models import AnimalStatus
from kkp.schemas.common import PaginationQuery


class AnimalQuery(PaginationQuery):
    order: Literal["asc", "desc"] = "asc"
    order_by: Literal["id", "updated_at"] = "id"
    id: int | None = None
    status: AnimalStatus | None = None
