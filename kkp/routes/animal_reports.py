from datetime import datetime, timedelta

from fastapi import APIRouter, Query
from loguru import logger
from pytz import UTC

from kkp.config import FCM
from kkp.db.point import Point, STDistanceSphere
from kkp.dependencies import JwtAuthVetDep, AnimalReportDep, JwtAuthVetDepN, JwtMaybeAuthUserDep
from kkp.models import Animal, Media, AnimalStatus, GeoPoint, AnimalReport, UserRole, Session, MediaStatus, \
    AnimalUpdate, AnimalUpdateType
from kkp.schemas.animal_reports import CreateAnimalReportsRequest, AnimalReportInfo, RecentReportsQuery, \
    MyAnimalReportsQuery
from kkp.schemas.common import PaginationResponse
from kkp.utils.cache import Cache
from kkp.utils.custom_exception import CustomMessageException

router = APIRouter(prefix="/animal-reports")


@router.post("", response_model=AnimalReportInfo)
async def create_animal_report(user: JwtMaybeAuthUserDep, data: CreateAnimalReportsRequest):
    location = await GeoPoint.get_near(data.latitude, data.longitude)
    if location is None:
        location = await GeoPoint.create(name=None, latitude=data.latitude, longitude=data.longitude)

    if data.animal_id is not None:
        if (animal := await Animal.get_or_none(id=data.animal_id)) is None:
            raise CustomMessageException("Unknown animal!", 404)
    elif data.name is not None and data.breed is not None:
        animal = await Animal.create(
            name=data.name, breed=data.breed, status=AnimalStatus.FOUND, current_location=location,
        )
    else:
        raise CustomMessageException("You need to specify either animal id or name and breed!", 400)

    report = await AnimalReport.create(reported_by=user, animal=animal, notes=data.notes, location=location)
    media = await Media.filter(id__in=data.media_ids, uploaded_by=user, status=MediaStatus.UPLOADED)
    await report.media.add(*media)
    await animal.medias.add(*media)
    await Cache.delete_obj(animal)

    await AnimalUpdate.create(animal=animal, type=AnimalUpdateType.REPORT, animal_report=report)

    session_query = Session.filter(
        location_time__gt=datetime.now(UTC) - timedelta(days=14), fcm_token__not=None,
        user__role__in=(UserRole.VET, UserRole.VOLUNTEER),
    ) \
        .annotate(dist=STDistanceSphere("location", location.point)) \
        .filter(dist__lt=25000)

    for session in await session_query:  # pragma: no cover
        try:
            await FCM.send_notification(
                "New animal needs your help!",
                f"Name: {animal.name}\nBreed: {animal.breed}\nNotes: {report.notes}",
                device_token=session.fcm_token,
            )
        except Exception as e:
            logger.opt(exception=e).warning(
                f"Failed to send notification to session {session.id} ({session.fcm_token!r})"
            )

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


@router.get("/my", response_model=PaginationResponse[AnimalReportInfo])
async def get_my_reports(user: JwtAuthVetDep, query: MyAnimalReportsQuery = Query()):
    reports_query = AnimalReport.filter(assigned_to=user, treatmentreports=None)

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


@router.get("/{report_id}", response_model=AnimalReportInfo)
async def get_animal_report(user: JwtMaybeAuthUserDep, report: AnimalReportDep):
    if user is not None:
        if user.role <= UserRole.REGULAR and report.reported_by_id != user.id:
            raise CustomMessageException("Insufficient privileges.", 403)
    else:
        if report.reported_by_id is not None:
            raise CustomMessageException("Insufficient privileges.", 403)

    return await report.to_json()


@router.post("/{report_id}/assign", response_model=AnimalReportInfo)
async def assign_animal_report_to_user(user: JwtAuthVetDep, report: AnimalReportDep):
    if report.assigned_to is not None:
        raise CustomMessageException("This report is already assigned to user.", 400)

    report.assigned_to = user
    await report.save(update_fields=["assigned_to_id"])
    await Cache.delete_obj(report)

    return await report.to_json()