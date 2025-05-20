from fastapi import APIRouter, Query

from kkp.dependencies import DonationGoalDep
from kkp.models import DonationGoal, Donation
from kkp.schemas.common import PaginationResponse
from kkp.schemas.donations import DonationGoalsQuery, GoalDonationsQuery, DonationGoalInfo, DonationInfo

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
            goal.to_json()
            for goal in await goals_query \
                .limit(query.page_size) \
                .offset(query.page_size * (query.page - 1))
        ],
    }


@router.get("/{goal_id}", response_model=DonationGoalInfo)
async def get_goal(goal: DonationGoalDep):
    return goal.to_json()


@router.get("/{goal_id}/donations", response_model=PaginationResponse[DonationInfo])
async def get_goal_donations(goal: DonationGoalDep, query: GoalDonationsQuery = Query()):
    donations_query = Donation.filter(goal=goal)

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


# TODO: add creating donations
