from fastapi import APIRouter

from kkp.dependencies import JwtAuthUserDep
from kkp.models import Animal, Media, AnimalStatus, GeoPoint, AnimalReport
from kkp.schemas.animal_reports import CreateAnimalReportsRequest

router = APIRouter(prefix="/animal-reports")


@router.post("", response_model=CreateAnimalReportsRequest)
async def create_animal_report(user: JwtAuthUserDep, data: CreateAnimalReportsRequest):
    # TODO: search for existing GeoPoints in 10-25m radius instead of creating new every time
    #  note to myself: it requires changing GeoPoint latitude and longitude to some database-native spatial column type
    #  (e.g. POINT in MariaDB)
    location = await GeoPoint.create(name=None, latitude=data.latitude, longitude=data.longitude)

    # TODO: handle already existing animals
    animal = await Animal.create(
        name=data.name, breed=data.breed, status=AnimalStatus.FOUND, current_location=location,
    )
    report = await AnimalReport.create(reported_by=user, animal=animal, notes=data.notes)
    media = await Media.filter(id__in=data.media_ids, uploaded_by=user)
    await report.media.add(*media)

    # TODO: send notification to near vets and volunteers

    return await report.to_json()
