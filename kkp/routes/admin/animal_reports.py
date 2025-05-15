from fastapi import APIRouter, Query

from fastapi import APIRouter, Query

from kkp.dependencies import JwtAuthAdminDepN, AnimalReportDep
from kkp.models import AnimalReport, User
from kkp.schemas.admin.animal_reports import EditAnimalReportRequest
from kkp.schemas.animal_reports import AnimalReportInfo
from kkp.schemas.animals import AnimalInfo
from kkp.schemas.common import PaginationResponse, PaginationQuery
from kkp.utils.custom_exception import CustomMessageException

router = APIRouter(prefix="/animal-reports", dependencies=[JwtAuthAdminDepN])


@router.get("", response_model=PaginationResponse[AnimalReportInfo])
async def get_animal_reports(query: PaginationQuery = Query()):
    return {
        "count": await AnimalReport.all().count(),
        "result": [
            await report.to_json()
            for report in await AnimalReport.all() \
                .limit(query.page_size) \
                .offset(query.page_size * (query.page - 1))
        ],
    }


@router.get("/{report_id}", response_model=AnimalReportInfo)
async def get_animal_report(report: AnimalReportDep):
    return await report.to_json()


@router.patch("/{report_id}", response_model=AnimalInfo)
async def edit_animal_report(report: AnimalReportDep, data: EditAnimalReportRequest):
    update_fields = []
    if data.assigned_to_id:
        if (new_assigned := await User.get_or_none(id=data.assigned_to_id)) is None:
            raise CustomMessageException("Unknown user.", 404)
        report.assigned_to = new_assigned
        update_fields.append("assigned_to_id")
    if data.notes:
        report.notes = data.notes
        update_fields.append("notes")

    if update_fields:
        await report.save(update_fields=update_fields)

    return await report.to_json()


@router.delete("/{report_id}", status_code=204)
async def delete_animal_report(report: AnimalReportDep):
    await report.delete()