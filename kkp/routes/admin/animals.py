from datetime import datetime

from fastapi import APIRouter, Query
from pytz import UTC

from kkp.dependencies import JwtAuthAdminDepN, AdminAnimalDep
from kkp.models import Media, Animal, MediaStatus, GeoPoint
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
    if data.remove_media_ids is not None:
        medias = await Media.filter(id__in=data.remove_media_ids, status=MediaStatus.UPLOADED)
        if medias:
            await animal.medias.remove(*medias)
    if data.add_media_ids is not None:
        medias = await Media.filter(id__in=data.add_media_ids, status=MediaStatus.UPLOADED)
        if medias:
            await animal.medias.add(*medias)

    update_data = data.model_dump(exclude_defaults=True, exclude={
        "add_media_ids", "remove_media_ids", "current_latitude", "current_longitude",
    })

    update_fields = list(update_data.keys())
    if data.current_latitude is not None and data.current_longitude is not None:
        location = await GeoPoint.get_near(data.current_latitude, data.current_longitude)
        if location is None:
            location = await GeoPoint.create(latitude=data.current_latitude, longitude=data.current_longitude)
        animal.current_location = location
        update_fields.append("current_location_id")

    if not update_fields:
        return await animal.to_json()

    update_data["updated_at"] = datetime.now(UTC)
    animal.update_from_dict(update_data)
    await animal.save(update_fields=update_fields)

    return await animal.to_json()


@router.delete("/{animal_id}", status_code=204)
async def delete_animal(animal: AdminAnimalDep):
    await animal.delete()