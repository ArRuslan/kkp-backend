from fastapi import APIRouter, Query

from kkp.dependencies import JwtAuthUserDep, AnimalDep
from kkp.schemas.animals import AnimalInfo
from kkp.schemas.common import PaginationResponse, PaginationQuery

router = APIRouter(prefix="/subscriptions")


@router.get("", response_model=PaginationResponse[AnimalInfo])
async def get_user_subscriptions(user: JwtAuthUserDep, query: PaginationQuery = Query()):
    return {
        "count": await user.subscriptions.all().count(),
        "result": [
            await animal.to_json(user)
            for animal in await user.subscriptions\
                .offset((query.page - 1) * query.page_size)\
                .limit(query.page_size)
        ],
    }


@router.put("/{animal_id}", status_code=204)
async def subscribe_to_animal(user: JwtAuthUserDep, animal: AnimalDep):
    await user.subscriptions.add(animal)


@router.delete("/{animal_id}", status_code=204)
async def unsubscribe_from_animal(user: JwtAuthUserDep, animal: AnimalDep):
    await user.subscriptions.remove(animal)
