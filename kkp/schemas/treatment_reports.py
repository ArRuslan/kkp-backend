from pydantic import BaseModel, EmailStr

from kkp.models import PayoutStatus
from kkp.schemas.animal_reports import AnimalReportInfo
from kkp.schemas.vet_clinics import VetClinicInfo


class CreateTreatmentReportRequest(BaseModel):
    animal_report_id: int
    description: str
    money_spent: float
    payout_email: EmailStr | None = None


class TreatmentReportInfo(BaseModel):
    id: int
    animal_report: AnimalReportInfo
    description: str
    money_spent: float
    created_at: int
    payout_status: PayoutStatus
    vet_clinic: VetClinicInfo | None
