from datetime import datetime

from fastapi import APIRouter, Query
from pytz import UTC
from tortoise.expressions import Subquery

from kkp.dependencies import JwtAuthUserDep, AnimalDep
from kkp.models import AnimalUpdate
from kkp.schemas.animal_updates import AnimalUpdatesQuery, AnimalUpdateInfo
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


@router.get("/updates", response_model=PaginationResponse[AnimalUpdateInfo])
async def get_user_subscriptions_updates(user: JwtAuthUserDep, query: AnimalUpdatesQuery = Query()):
    updates_query = AnimalUpdate.filter(animal__id__in=Subquery(user.subscriptions.all().values_list("id", flat=True)))

    if query.before_date is not None:
        updates_query = updates_query.filter(date__lt=datetime.fromtimestamp(query.before_date, tz=UTC))
    if query.after_date is not None:
        updates_query = updates_query.filter(date__gt=datetime.fromtimestamp(query.after_date, tz=UTC))

    order = query.order_by
    if query.order == "desc":
        order = f"-{order}"

    updates_query = updates_query.order_by(order)

    return {
        "count": await updates_query.count(),
        "result": [
            await update.to_json()
            for update in await updates_query.select_related("animal", "animal_report", "treatment_report") \
                .limit(query.page_size) \
                .offset(query.page_size * (query.page - 1))
        ],
    }


@router.put("/{animal_id}", status_code=204)
async def subscribe_to_animal(user: JwtAuthUserDep, animal: AnimalDep):
    await user.subscriptions.add(animal)


@router.delete("/{animal_id}", status_code=204)
async def unsubscribe_from_animal(user: JwtAuthUserDep, animal: AnimalDep):
    await user.subscriptions.remove(animal)
