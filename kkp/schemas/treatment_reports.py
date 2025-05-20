from pydantic import BaseModel

from kkp.schemas.animal_reports import AnimalReportInfo
from kkp.schemas.vet_clinics import VetClinicInfo


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
    vet_clinic: VetClinicInfo | None
