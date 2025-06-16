from datetime import datetime, timedelta

from fastapi import APIRouter, Query, BackgroundTasks
from loguru import logger
from pytz import UTC
from tortoise.expressions import RawSQL
from tortoise.transactions import in_transaction

from kkp.config import FCM
from kkp.db.point import Point, mbr_contains_sql
from kkp.dependencies import JwtAuthVetDep, AnimalReportDep, JwtAuthVetDepN, JwtMaybeAuthUserDep
from kkp.models import Animal, Media, AnimalStatus, GeoPoint, AnimalReport, UserRole, Session, MediaStatus, \
    AnimalUpdate, AnimalUpdateType
from kkp.schemas.animal_reports import CreateAnimalReportsRequest, AnimalReportInfo, RecentReportsQuery, \
    MyAnimalReportsQuery
from kkp.schemas.common import PaginationResponse
from kkp.utils.cache import Cache
from kkp.utils.custom_exception import CustomMessageException

router = APIRouter(prefix="/animal-reports")


async def _send_notification_task(report: AnimalReport) -> None:
    animal = report.animal
    location = report.location

    point = location.point
    point_wkb = point.to_sql_wkb_bin().hex()
    radius_m = 25000
    radius = radius_m / 111320
    before_time = int((datetime.now(UTC) - timedelta(days=14)).timestamp())

    sessions = await Session.raw(f"""
            SELECT 
                `session`.`nonce`,`session`.`active`,`session`.`user_id`,`session`.`created_at`,`session`.`location`,
                `session`.`location_time`,`session`.`fcm_token`,`session`.`id`,`session`.`fcm_token_time`,
                ST_Distance_Sphere(`session`.`location`, x'{point_wkb}') `dist`
            FROM `session`
            LEFT OUTER JOIN `user` `session__user` ON `session__user`.`id`=`session`.`user_id`
            WHERE {mbr_contains_sql(point, radius, 'location')} 
                AND `session`.`location_time` > FROM_UNIXTIME({before_time}) 
                AND `session`.`fcm_token` IS NOT NULL 
                AND `session__user`.`role` IN ({UserRole.VET.value}, {UserRole.VOLUNTEER.value})
            HAVING `dist` < {radius_m} 
        """)

    for session in sessions:  # pragma: no cover
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


@router.post("", response_model=AnimalReportInfo)
async def create_animal_report(user: JwtMaybeAuthUserDep, data: CreateAnimalReportsRequest, bg: BackgroundTasks):
    location = await GeoPoint.get_near(data.latitude, data.longitude)
    if location is None:
        location = await GeoPoint.create(name=None, latitude=data.latitude, longitude=data.longitude)

    async with in_transaction():
        animal_created = False
        if data.animal_id is not None:
            if (animal := await Animal.get_or_none(id=data.animal_id)) is None:
                raise CustomMessageException("Unknown animal!", 404)
        elif data.name is not None and data.breed is not None:
            animal = await Animal.create(
                name=data.name, breed=data.breed, status=AnimalStatus.FOUND, current_location=location,
            )
            animal_created = True
        else:
            raise CustomMessageException("You need to specify either animal id or name and breed!", 400)

        report = await AnimalReport.create(reported_by=user, animal=animal, notes=data.notes, location=location)
        if data.media_ids:
            media = await Media.filter(id__in=data.media_ids, uploaded_by=user, status=MediaStatus.UPLOADED)
            await report.media.add(*media)
            await animal.medias.add(*media)
        if not animal_created:
            await Cache.delete_obj(animal)

        await AnimalUpdate.create(animal=animal, type=AnimalUpdateType.REPORT, animal_report=report)

    bg.add_task(_send_notification_task, report)

    return await report.to_json()


@router.get("/recent", response_model=PaginationResponse[AnimalReportInfo], dependencies=[JwtAuthVetDepN])
async def get_recent_unassigned_reports(query: RecentReportsQuery = Query()):
    point = Point(query.lon, query.lat)
    point_wkb = point.to_sql_wkb_bin().hex()
    radius_m = min(max(query.radius, 100), 10000)
    radius = radius_m / 111320
    after_time = int((datetime.now(UTC) - timedelta(hours=12)).timestamp())

    sql = f"""
    SELECT 
        COUNT(*) `all_count`,
        ST_Distance_Sphere(`location`.`point`, x'{point_wkb}') `dist`,
        `report`.`assigned_to_id`,`report`.`location_id`,`report`.`notes`,`report`.`created_at`,`report`.`animal_id`,`report`.`reported_by_id`,`report`.`id`,
        `assigned_to`.`password` `animalreport__assigned_to.password`,`assigned_to`.`email` `animalreport__assigned_to.email`,`assigned_to`.`mfa_key` `animalreport__assigned_to.mfa_key`,`assigned_to`.`last_name` `animalreport__assigned_to.last_name`,`assigned_to`.`viber_phone` `animalreport__assigned_to.viber_phone`,`assigned_to`.`telegram_username` `animalreport__assigned_to.telegram_username`,`assigned_to`.`whatsapp_phone` `animalreport__assigned_to.whatsapp_phone`,`assigned_to`.`role` `animalreport__assigned_to.role`,`assigned_to`.`first_name` `animalreport__assigned_to.first_name`,`assigned_to`.`id` `animalreport__assigned_to.id`,
        `reported_by`.`password` `animalreport__reported_by.password`,`reported_by`.`email` `animalreport__reported_by.email`,`reported_by`.`mfa_key` `animalreport__reported_by.mfa_key`,`reported_by`.`last_name` `animalreport__reported_by.last_name`,`reported_by`.`viber_phone` `animalreport__reported_by.viber_phone`,`reported_by`.`telegram_username` `animalreport__reported_by.telegram_username`,`reported_by`.`whatsapp_phone` `animalreport__reported_by.whatsapp_phone`,`reported_by`.`role` `animalreport__reported_by.role`,`reported_by`.`first_name` `animalreport__reported_by.first_name`,`reported_by`.`id` `animalreport__reported_by.id`,
        `location`.`longitude` `animalreport__location.longitude`,`location`.`point` `animalreport__location.point`,`location`.`name` `animalreport__location.name`,`location`.`latitude` `animalreport__location.latitude`,`location`.`id` `animalreport__location.id`,
        `animal`.`status` `animalreport__animal.status`,`animal`.`gender` `animalreport__animal.gender`,`animal`.`updated_at` `animalreport__animal.updated_at`,`animal`.`breed` `animalreport__animal.breed`,`animal`.`description` `animalreport__animal.description`,`animal`.`name` `animalreport__animal.name`,`animal`.`current_location_id` `animalreport__animal.current_location_id`,`animal`.`id` `animalreport__animal.id`
    FROM `animalreport` `report`
    LEFT OUTER JOIN `geopoint` `location` ON `location`.`id`=`report`.`location_id`
    LEFT OUTER JOIN `user` `assigned_to` ON `assigned_to`.`id`=`report`.`assigned_to_id`
    LEFT OUTER JOIN `user` `reported_by` ON `reported_by`.`id`=`report`.`reported_by_id`
    LEFT OUTER JOIN `animal` `animal` ON `animal`.`id`=`report`.`animal_id`
    WHERE {mbr_contains_sql(point, radius_m, 'location`.`point')} 
        AND `report`.`created_at` > FROM_UNIXTIME({after_time}) 
        AND `report`.`assigned_to_id` IS NULL 
    HAVING `dist` < {radius_m}
    ORDER BY `report`.`id` DESC
    LIMIT {query.page_size}
    OFFSET {query.page_size * (query.page - 1)}
    """

    db = AnimalReport._choose_db()
    sql = RawSQL(sql).get_sql(db.query_class.SQL_CONTEXT)
    reports = await db.executor_class(model=AnimalReport, db=db).execute_select(sql, [], ["all_count"])
    all_count = reports[0].all_count if reports else 0

    return {
        "count": all_count,
        "result": [
            await report.to_json()
            for report in reports
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