from datetime import datetime

from fastapi import APIRouter, Query
from pytz import UTC

from kkp.dependencies import AnimalDep, JwtAuthUserDepN, JwtAuthVetDepN, JwtMaybeAuthUserDep
from kkp.models import Animal, Media, AnimalReport, TreatmentReport
from kkp.schemas.admin.animals import AnimalQuery
from kkp.schemas.animal_reports import AnimalReportInfo
from kkp.schemas.animals import AnimalInfo, EditAnimalRequest
from kkp.schemas.common import PaginationResponse, PaginationQuery
from kkp.schemas.treatment_reports import TreatmentReportInfo

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
    media_ids = data.media_ids
    data = data.model_dump(exclude_defaults=True, exclude={"media_ids"})
    if media_ids is not None:
        # TODO: diff update?
        medias = await Media.filter(id__in=data.media_ids)
        await animal.medias.clear()
        await animal.medias.add(*medias)

    if not data:
        return await animal.to_json()

    update_fields = list(data.keys())
    if "current_location" in data:
        field_idx = update_fields.index("current_location")
        update_fields[field_idx] += "_id"

    data["updated_at"] = datetime.now(UTC)
    animal.update_from_dict(data)
    await animal.save(update_fields=list(data.keys()))

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
