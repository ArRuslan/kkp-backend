from datetime import datetime

from fastapi import APIRouter, Query
from pytz import UTC

from kkp.dependencies import DonationGoalDep, JwtMaybeAuthUserDep
from kkp.models import DonationGoal, Donation, DonationStatus
from kkp.schemas.common import PaginationResponse
from kkp.schemas.donations import DonationGoalsQuery, GoalDonationsQuery, DonationGoalInfo, DonationInfo, \
    CreateDonationRequest, DonationCreatedInfo
from kkp.utils.cache import Cache
from kkp.utils.custom_exception import CustomMessageException
from kkp.utils.paypal import PayPal

router = APIRouter(prefix="/donations")


@router.get("", response_model=PaginationResponse[DonationGoalInfo])
async def get_goals(query: DonationGoalsQuery = Query()):
    goals_query = DonationGoal.filter()

    order = query.order_by
    if query.order == "desc":
        order = f"-{order}"

    goals_query = goals_query.order_by(order)

    return {
        "count": await goals_query.count(),
        "result": [
            await goal.to_json()
            for goal in await goals_query \
                .limit(query.page_size) \
                .offset(query.page_size * (query.page - 1))
        ],
    }


@router.get("/{goal_id}", response_model=DonationGoalInfo)
async def get_goal(goal: DonationGoalDep):
    return await goal.to_json()


@router.get("/{goal_id}/donations", response_model=PaginationResponse[DonationInfo])
async def get_goal_donations(goal: DonationGoalDep, query: GoalDonationsQuery = Query()):
    donations_query = Donation.filter(goal=goal, status=DonationStatus.PROCESSED)

    order = query.order_by
    if query.order == "desc":
        order = f"-{order}"

    donations_query = donations_query.order_by(order)

    return {
        "count": await donations_query.count(),
        "result": [
            await donation.to_json()
            for donation in await donations_query.select_related("user", "goal") \
                .limit(query.page_size) \
                .offset(query.page_size * (query.page - 1))
        ],
    }


@router.post("/{goal_id}/donate", response_model=DonationCreatedInfo)
async def create_donation(user: JwtMaybeAuthUserDep, goal: DonationGoalDep, data: CreateDonationRequest):
    if goal.ended_at is not None:
        raise CustomMessageException("This donation goal ended")

    paypal_id = await PayPal.create(data.amount)
    donation = await Donation.create(
        goal=goal,
        status=DonationStatus.CREATED,
        user=user if not data.anonymous else None,
        amount=data.amount,
        comment=data.comment,
        paypal_id=paypal_id,
    )

    return {
        "id": donation.id,
        "paypal_id": paypal_id,
    }


@router.post("/{goal_id}/donations/{donation_id}", response_model=DonationInfo)
async def process_payment(goal: DonationGoalDep, donation_id: int):
    if (donation := await Donation.get_or_none(id=donation_id, goal=goal, status=DonationStatus.CREATED)) is None:
        raise CustomMessageException("Unknown donation or it was already processed")

    if await PayPal.capture(donation.paypal_id) is None:
        raise CustomMessageException("Failed to capture payment")

    donation.status = DonationStatus.PROCESSED
    await donation.save(update_fields=["status"])
    await Cache.delete_obj(donation)

    update_goal = ["got_amount"]
    goal.got_amount += donation.amount
    if goal.got_amount >= goal.need_amount:
        goal.ended_at = datetime.now(UTC)
        update_goal.append("ended_at")

    await goal.save(update_fields=update_goal)
    await Cache.delete_obj(goal)

    return await donation.to_json()
