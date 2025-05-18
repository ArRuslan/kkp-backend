from fastapi import APIRouter, Query

from kkp.dependencies import JwtAuthAdminDepN, AdminTreatmentReportDep
from kkp.models import TreatmentReport
from kkp.schemas.admin.treatment_reports import ReportsQuery
from kkp.schemas.common import PaginationResponse
from kkp.schemas.treatment_reports import TreatmentReportInfo

router = APIRouter(prefix="/treatment-reports", dependencies=[JwtAuthAdminDepN])


@router.get("", response_model=PaginationResponse[TreatmentReportInfo])
async def get_treatment_reports(query: ReportsQuery = Query()):
    reports_query = TreatmentReport.filter()

    if query.id is not None:
        reports_query = reports_query.filter(id=query.id)
    if query.report_id is not None:
        reports_query = reports_query.filter(report__id=query.report_id)

    order = query.order_by
    if query.order == "desc":
        order = f"-{order}"

    reports_query = reports_query.order_by(order)

    return {
        "count": await reports_query.count(),
        "result": [
            await report.to_json()
            for report in await reports_query \
                .limit(query.page_size) \
                .offset(query.page_size * (query.page - 1))
        ],
    }


@router.get("/{treatment_report_id}", response_model=TreatmentReportInfo)
async def get_treatment_report(report: AdminTreatmentReportDep):
    return await report.to_json()


@router.delete("/{treatment_report_id}", status_code=204)
async def delete_animal_report(report: AdminTreatmentReportDep):
    await report.delete()