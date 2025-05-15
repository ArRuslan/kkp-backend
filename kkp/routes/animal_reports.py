from datetime import datetime, timedelta

from fastapi import APIRouter, Query
from pytz import UTC

from kkp.db.point import Point, STDistanceSphere
from kkp.dependencies import JwtAuthUserDep, JwtAuthVetDep, AnimalReportDep, JwtAuthVetDepN
from kkp.models import Animal, Media, AnimalStatus, GeoPoint, AnimalReport, UserRole
from kkp.schemas.animal_reports import CreateAnimalReportsRequest, AnimalReportInfo, RecentReportsQuery
from kkp.schemas.common import PaginationResponse
from kkp.utils.custom_exception import CustomMessageException

router = APIRouter(prefix="/animal-reports")


@router.post("", response_model=AnimalReportInfo)
async def create_animal_report(user: JwtAuthUserDep, data: CreateAnimalReportsRequest):
    location = await GeoPoint.get_near(data.latitude, data.longitude)
    if location is None:
        location = await GeoPoint.create(name=None, latitude=data.latitude, longitude=data.longitude)

    # TODO: handle already existing animals
    animal = await Animal.create(
        name=data.name, breed=data.breed, status=AnimalStatus.FOUND, current_location=location,
    )
    report = await AnimalReport.create(reported_by=user, animal=animal, notes=data.notes, location=location)
    media = await Media.filter(id__in=data.media_ids, uploaded_by=user)
    await report.media.add(*media)

    # TODO: send notification to near vets and volunteers

    return await report.to_json()


@router.get("/recent", response_model=PaginationResponse[AnimalReportInfo], dependencies=[JwtAuthVetDepN])
async def get_recent_unassigned_reports(query: RecentReportsQuery = Query()):
    radius = min(max(query.radius, 100), 10000)
    db_query = AnimalReport.filter(created_at__gt=datetime.now(UTC) - timedelta(hours=12), assigned_to=None) \
        .select_related("reported_by", "assigned_to", "animal", "location")\
        .annotate(dist=STDistanceSphere("location__point", Point(query.lon, query.lat))) \
        .filter(dist__lt=radius) \
        .order_by("-id")

    return {
        "count": await db_query.count(),
        "result": [
            await report.to_json()
            for report in await db_query.limit(query.page_size).offset(query.page_size * (query.page - 1))
        ],
    }


@router.get("/{report_id}", response_model=AnimalReportInfo)
async def get_animal_report(user: JwtAuthUserDep, report: AnimalReportDep):
    if user.role <= UserRole.REGULAR and report.reported_by_id != user.id:
        raise CustomMessageException("Insufficient privileges.", 403)

    return await report.to_json()


@router.post("/{report_id}/assign", response_model=AnimalReportInfo)
async def assign_animal_report_to_user(user: JwtAuthVetDep, report: AnimalReportDep):
    if report.assigned_to is not None:
        raise CustomMessageException("This report is already assigned to user.", 400)

    report.assigned_to = user
    await report.save(update_fields=["assigned_to_id"])

    return await report.to_json()