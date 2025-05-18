from typing import Literal

from pydantic import BaseModel

from kkp.schemas.common import PaginationQuery


class EditAnimalReportRequest(BaseModel):
    assigned_to_id: int | None = None
    notes: str | None = None


class AnimalReportsQuery(PaginationQuery):
    order: Literal["asc", "desc"] = "asc"
    order_by: Literal["id", "created_at"] = "id"
    id: int | None = None
    reported_by_id: int | None = None
    animal_id: int | None = None
    assigned_to_id: int | None = None

