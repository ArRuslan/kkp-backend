from fastapi import APIRouter

from kkp.dependencies import JwtAuthUserDep, JwtAuthVetDep, TreatmentReportDep
from kkp.models import AnimalReport, UserRole, TreatmentReport
from kkp.schemas.treatment_reports import TreatmentReportInfo, CreateTreatmentReportRequest
from kkp.utils.custom_exception import CustomMessageException

router = APIRouter(prefix="/treatment-reports")


@router.post("", response_model=TreatmentReportInfo)
async def create_treatment_report(user: JwtAuthVetDep, data: CreateTreatmentReportRequest):
    if (report := await AnimalReport.get_or_none(id=data.animal_report_id).select_related("assigned_to")) is None:
        raise CustomMessageException("Unknown report.", 404)
    if report.assigned_to != user:
        raise CustomMessageException("This report was assigned to different user.", 400)

    treatment_report = await TreatmentReport.create(
        report=report, description=data.description, money_spent=data.money_spent,
    )

    return await treatment_report.to_json()


@router.get("/{treatment_report_id}", response_model=TreatmentReportInfo)
async def get_treatment_report(user: JwtAuthUserDep, report: TreatmentReportDep):
    if user.role <= UserRole.REGULAR and report.report.reported_by_id != user.id:
        raise CustomMessageException("Insufficient privileges.", 403)

    return await report.to_json()
