from datetime import datetime

from fastapi import APIRouter, Query
from pytz import UTC

from kkp.dependencies import JwtAuthAdminDepN, AdminAnimalDep
from kkp.models import Media, Animal
from kkp.schemas.admin.animals import AnimalQuery
from kkp.schemas.animals import AnimalInfo, EditAnimalRequest
from kkp.schemas.common import PaginationResponse

router = APIRouter(prefix="/animals", dependencies=[JwtAuthAdminDepN])


@router.get("", response_model=PaginationResponse[AnimalInfo])
async def get_animals(query: AnimalQuery = Query()):
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
            await animal.to_json()
            for animal in await animals_query \
                .limit(query.page_size) \
                .offset(query.page_size * (query.page - 1))
        ],
    }


@router.get("/{animal_id}", response_model=AnimalInfo)
async def get_animal(animal: AdminAnimalDep):
    return await animal.to_json()


@router.patch("/{animal_id}", response_model=AnimalInfo)
async def edit_animal(animal: AdminAnimalDep, data: EditAnimalRequest):
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
async def delete_animal(animal: AdminAnimalDep):
    await animal.delete()