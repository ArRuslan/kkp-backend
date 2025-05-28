from fastapi import APIRouter, Query

from kkp.dependencies import JwtAuthAdminDepN, AnimalReportDep
from kkp.models import AnimalReport, User
from kkp.schemas.admin.animal_reports import EditAnimalReportRequest, AnimalReportsQuery
from kkp.schemas.animal_reports import AnimalReportInfo
from kkp.schemas.common import PaginationResponse
from kkp.utils.cache import Cache
from kkp.utils.custom_exception import CustomMessageException

router = APIRouter(prefix="/animal-reports", dependencies=[JwtAuthAdminDepN])


@router.get("", response_model=PaginationResponse[AnimalReportInfo])
async def get_animal_reports(query: AnimalReportsQuery = Query()):
    reports_query = AnimalReport.filter()

    if query.id is not None:
        reports_query = reports_query.filter(id=query.id)
    if query.assigned_to_id is not None:
        reports_query = reports_query.filter(assigned_to__id=query.assigned_to_id)
    if query.reported_by_id is not None:
        reports_query = reports_query.filter(reported_by__id=query.reported_by_id)
    if query.animal_id is not None:
        reports_query = reports_query.filter(animal__id=query.animal_id)

    order = query.order_by
    if query.order == "desc":
        order = f"-{order}"

    reports_query = reports_query.order_by(order)

    Cache.disable()
    return {
        "count": await reports_query.count(),
        "result": [
            await report.to_json()
            for report in await reports_query \
                .limit(query.page_size) \
                .offset(query.page_size * (query.page - 1))
        ],
    }


@router.get("/{report_id}", response_model=AnimalReportInfo)
async def get_animal_report(report: AnimalReportDep):
    Cache.disable()
    return await report.to_json()


@router.patch("/{report_id}", response_model=AnimalReportInfo)
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