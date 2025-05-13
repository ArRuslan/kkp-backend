from datetime import datetime

from fastapi import APIRouter, Query
from pytz import UTC

from kkp.dependencies import JwtAuthUserDep, AnimalDep, JwtAuthVetDep, JwtAuthUserDepN
from kkp.models import Animal, Media, AnimalReport, TreatmentReport
from kkp.schemas.animal_reports import AnimalReportInfo
from kkp.schemas.animals import AnimalInfo, CreateAnimalRequest, EditAnimalRequest
from kkp.schemas.common import PaginationResponse, PaginationQuery
from kkp.schemas.treatment_reports import TreatmentReportInfo

router = APIRouter(prefix="/animals", deprecated=True)


@router.get("", response_model=PaginationResponse[AnimalInfo])
async def get_animals(user: JwtAuthUserDep, query: PaginationQuery = Query()):
    """ Probably will be deleted or moved to admin api because this route allows any user to view ALL animals """

    return {
        "count": await Animal.all().count(),
        "result": [
            await animal.to_json()
            for animal in await Animal.all()\
                .limit(query.page_size)\
                .offset(query.page_size * (query.page - 1))
        ],
    }


# TODO: save user somewhere (audit logs, animal status, report, etc.)
@router.post("", response_model=AnimalInfo, deprecated=True)
async def add_animal(user: JwtAuthUserDep, data: CreateAnimalRequest):
    """ Probably will be deleted or moved to admin api because animals should be added via found animal reports (?) """

    medias = await Media.filter(id__in=data.media_ids)
    animal = await Animal.create(**data.model_dump(exclude={"media_ids"}))
    await animal.medias.add(*medias)

    return await animal.to_json()


@router.get("/{animal_id}", response_model=AnimalInfo)
async def get_animal(animal: AnimalDep):
    """ Idk if it is a good idea to allow any user (even unauthenticated ones) to get any animal """
    return await animal.to_json()


@router.patch("/{animal_id}", response_model=AnimalInfo)
async def edit_animal(user: JwtAuthVetDep, animal: AnimalDep, data: EditAnimalRequest):
    """ Probably will be deleted or moved to vet api """

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


@router.delete("/{animal_id}", status_code=204)
async def delete_animal(user: JwtAuthVetDep, animal: AnimalDep):
    """ Probably will be deleted or moved to admin api """

    await animal.delete()


@router.get("/{animal_id}/reports", response_model=PaginationResponse[AnimalReportInfo], dependencies=[JwtAuthUserDepN], deprecated=False)
async def get_animals(animal: AnimalDep, query: PaginationQuery = Query()):
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
async def get_animals(animal: AnimalDep, query: PaginationQuery = Query()):
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
