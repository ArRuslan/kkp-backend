from pydantic import BaseModel

from kkp.schemas.animal_reports import AnimalReportInfo
from kkp.schemas.animals import AnimalInfo
from kkp.schemas.common import GeoPointInfo
from kkp.schemas.media import MediaInfo
from kkp.schemas.users import UserBaseInfo


class CreateTreatmentReportRequest(BaseModel):
    animal_report_id: int
    description: str
    money_spent: float


class TreatmentReportInfo(BaseModel):
    id: int
    animal_report: AnimalReportInfo
    description: str
    money_spent: float
    created_at: int
