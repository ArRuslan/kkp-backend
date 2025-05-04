from fastapi import APIRouter, Query

from kkp.dependencies import JwtAuthUserDep, AnimalDep, JwtAuthVetDep
from kkp.models import Animal, Media
from kkp.schemas.animals import AnimalInfo, CreateAnimalRequest, EditAnimalRequest
from kkp.schemas.common import PaginationResponse, PaginationQuery

router = APIRouter(prefix="/animals")


@router.get("", response_model=PaginationResponse[AnimalInfo])
async def get_animals(user: JwtAuthUserDep, query: PaginationQuery = Query()):
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
@router.post("", response_model=AnimalInfo)
async def add_animal(user: JwtAuthUserDep, data: CreateAnimalRequest):
    medias = await Media.filter(id__in=data.media_ids)
    animal = await Animal.create(**data.model_dump(exclude={"media_ids"}))
    await animal.medias.add(*medias)

    return await animal.to_json()


@router.get("/{animal_id}", response_model=AnimalInfo)
async def get_animal(animal: AnimalDep):
    return await animal.to_json()


@router.patch("/{animal_id}", response_model=AnimalInfo)
async def edit_animal(user: JwtAuthVetDep, animal: AnimalDep, data: EditAnimalRequest):
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

    animal.update_from_dict(data)
    await animal.save(update_fields=list(data.keys()))

    return await animal.to_json()


@router.delete("/{animal_id}", status_code=204)
async def delete_animal(user: JwtAuthVetDep, animal: AnimalDep):
    await animal.delete()