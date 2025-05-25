from typing import Literal

from pydantic import BaseModel

from kkp.models import AnimalUpdateType
from kkp.schemas.animal_reports import AnimalReportInfo
from kkp.schemas.animals import AnimalInfo
from kkp.schemas.common import PaginationQuery
from kkp.schemas.treatment_reports import TreatmentReportInfo


class AnimalUpdateInfo(BaseModel):
    id: int
    animal: AnimalInfo
    type: AnimalUpdateType
    date: int
    animal_report: AnimalReportInfo | None
    treatment_report: TreatmentReportInfo | None


class AnimalUpdatesQuery(PaginationQuery):
    order: Literal["asc", "desc"] = "desc"
    order_by: Literal["date"] = "date"
    after_date: int | None = None
    before_date: int | None = None
