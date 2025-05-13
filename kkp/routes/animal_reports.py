from fastapi import APIRouter

from kkp.db.point import Point, STDistanceSphere
from kkp.dependencies import JwtAuthUserDep, JwtAuthVetDep, AnimalReportDep
from kkp.models import Animal, Media, AnimalStatus, GeoPoint, AnimalReport, UserRole
from kkp.schemas.animal_reports import CreateAnimalReportsRequest, AnimalReportInfo
from kkp.utils.custom_exception import CustomMessageException

router = APIRouter(prefix="/animal-reports")


@router.post("", response_model=AnimalReportInfo)
async def create_animal_report(user: JwtAuthUserDep, data: CreateAnimalReportsRequest):
    location = await GeoPoint\
        .annotate(dist=STDistanceSphere("point", Point(data.longitude, data.latitude)))\
        .filter(dist__lt=100)\
        .order_by("dist")\
        .first()
    if location is None:
        location = await GeoPoint.create(
            name=None, latitude=data.latitude, longitude=data.longitude, point=Point(data.longitude, data.latitude),
        )

    # TODO: handle already existing animals
    animal = await Animal.create(
        name=data.name, breed=data.breed, status=AnimalStatus.FOUND, current_location=location,
    )
    report = await AnimalReport.create(reported_by=user, animal=animal, notes=data.notes)
    media = await Media.filter(id__in=data.media_ids, uploaded_by=user)
    await report.media.add(*media)

    # TODO: send notification to near vets and volunteers

    return await report.to_json()


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
