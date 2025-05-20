from datetime import datetime

from fastapi import APIRouter
from pytz import UTC

from kkp.dependencies import JwtAuthUserDep, JwtAuthVetDep, TreatmentReportDep
from kkp.models import AnimalReport, UserRole, TreatmentReport, VetClinic
from kkp.schemas.treatment_reports import TreatmentReportInfo, CreateTreatmentReportRequest
from kkp.utils.custom_exception import CustomMessageException

router = APIRouter(prefix="/treatment-reports")


@router.post("", response_model=TreatmentReportInfo)
async def create_treatment_report(user: JwtAuthVetDep, data: CreateTreatmentReportRequest):
    report_related = ("assigned_to", "animal",)
    if (report := await AnimalReport.get_or_none(id=data.animal_report_id).select_related(*report_related)) is None:
        raise CustomMessageException("Unknown report.", 404)
    if report.assigned_to != user:
        raise CustomMessageException("This report was assigned to different user.", 400)

    vet_clinic = await VetClinic.filter(employees__id=user.id).first()

    treatment_report = await TreatmentReport.create(
        report=report, description=data.description, money_spent=data.money_spent, vet_clinic=vet_clinic,
    )
    report.animal.updated_at = datetime.now(UTC)
    await report.animal.save(update_fields=["updated_at"])

    return await treatment_report.to_json()


@router.get("/{treatment_report_id}", response_model=TreatmentReportInfo)
async def get_treatment_report(user: JwtAuthUserDep, report: TreatmentReportDep):
    if user.role <= UserRole.REGULAR and report.report.reported_by_id != user.id:
        raise CustomMessageException("Insufficient privileges.", 403)

    return await report.to_json()
