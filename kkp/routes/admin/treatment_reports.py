from fastapi import APIRouter, Query

from kkp.dependencies import JwtAuthAdminDepN, AdminTreatmentReportDep
from kkp.models import TreatmentReport
from kkp.schemas.common import PaginationResponse, PaginationQuery
from kkp.schemas.treatment_reports import TreatmentReportInfo

router = APIRouter(prefix="/treatment-reports", dependencies=[JwtAuthAdminDepN])


@router.get("", response_model=PaginationResponse[TreatmentReportInfo])
async def get_treatment_reports(query: PaginationQuery = Query()):
    return {
        "count": await TreatmentReport.all().count(),
        "result": [
            await report.to_json()
            for report in await TreatmentReport.all() \
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