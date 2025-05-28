from datetime import datetime

from fastapi import APIRouter, Query
from pytz import UTC

from kkp.dependencies import AnimalDep, JwtAuthUserDepN, JwtAuthVetDepN, JwtMaybeAuthUserDep
from kkp.models import Animal, Media, AnimalReport, TreatmentReport, MediaStatus, GeoPoint, AnimalUpdateType, \
    AnimalUpdate
from kkp.schemas.admin.animals import AnimalQuery
from kkp.schemas.animal_reports import AnimalReportInfo
from kkp.schemas.animals import AnimalInfo, EditAnimalRequest
from kkp.schemas.common import PaginationResponse, PaginationQuery
from kkp.schemas.treatment_reports import TreatmentReportInfo
from kkp.utils.cache import Cache

router = APIRouter(prefix="/animals")


@router.get("", response_model=PaginationResponse[AnimalInfo])
async def get_animals(user: JwtMaybeAuthUserDep, query: AnimalQuery = Query()):
    animals_query = Animal.filter()

    if query.id is not None:
        animals_query = animals_query.filter(id=query.id)
    if query.status is not None:
        animals_query = animals_query.filter(status=query.status)

    order = query.order_by
    if query.order == "desc":
        order = f"-{order}"

    animals_query = animals_query.order_by(order)

    return {
        "count": await animals_query.count(),
        "result": [
            await animal.to_json(user)
            for animal in await animals_query \
                .limit(query.page_size) \
                .offset(query.page_size * (query.page - 1))
        ],
    }


@router.get("/{animal_id}", response_model=AnimalInfo)
async def get_animal(animal: AnimalDep, user: JwtMaybeAuthUserDep):
    return await animal.to_json(user)


@router.patch("/{animal_id}", response_model=AnimalInfo, dependencies=[JwtAuthVetDepN])
async def edit_animal(animal: AnimalDep, data: EditAnimalRequest):
    if data.remove_media_ids is not None:
        medias = await Media.filter(id__in=data.remove_media_ids, status=MediaStatus.UPLOADED)
        if medias:
            await animal.medias.remove(*medias)
            await Cache.delete_obj(animal)
    if data.add_media_ids is not None:
        medias = await Media.filter(id__in=data.add_media_ids, status=MediaStatus.UPLOADED)
        if medias:
            await animal.medias.add(*medias)
            await Cache.delete_obj(animal)

    update_data = data.model_dump(exclude_defaults=True, exclude={
        "add_media_ids", "remove_media_ids", "current_latitude", "current_longitude",
    })

    update_fields = list(update_data.keys())
    if data.current_latitude is not None and data.current_longitude is not None:
        location = await GeoPoint.get_near(data.current_latitude, data.current_longitude)
        if location is None:
            location = await GeoPoint.create(name=None, latitude=data.current_latitude, longitude=data.current_longitude)
        animal.current_location = location
        update_fields.append("current_location_id")

    if not update_fields:
        return await animal.to_json()

    update_data["updated_at"] = datetime.now(UTC)
    animal.update_from_dict(update_data)
    await animal.save(update_fields=update_fields)
    await Cache.delete_obj(animal)

    await AnimalUpdate.create(animal=animal, type=AnimalUpdateType.ANIMAL)

    return await animal.to_json()


@router.get("/{animal_id}/reports", response_model=PaginationResponse[AnimalReportInfo], dependencies=[JwtAuthUserDepN], deprecated=False)
async def get_animal_reports(animal: AnimalDep, query: PaginationQuery = Query()):
    return {
        "count": await AnimalReport.filter(animal=animal).count(),
        "result": [
            await report.to_json()
            for report in await AnimalReport.filter(animal=animal)\
                .select_related("reported_by", "assigned_to", "animal", "location")\
                .limit(query.page_size)\
                .offset(query.page_size * (query.page - 1))
        ],
    }


@router.get("/{animal_id}/treatment-reports", response_model=PaginationResponse[TreatmentReportInfo], dependencies=[JwtAuthUserDepN], deprecated=False)
async def get_animal_treatment_reports(animal: AnimalDep, query: PaginationQuery = Query()):
    return {
        "count": await TreatmentReport.filter(report__animal=animal).count(),
        "result": [
            await report.to_json()
            for report in await TreatmentReport.filter(report__animal=animal)\
                .select_related(
                "report", "report__reported_by", "report__assigned_to", "report__animal", "report__location"
                )\
                .limit(query.page_size)\
                .offset(query.page_size * (query.page - 1))
        ],
    }
