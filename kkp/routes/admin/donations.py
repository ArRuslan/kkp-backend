from fastapi import APIRouter

from kkp.dependencies import DonationGoalDep, JwtAuthAdminDepN
from kkp.models import DonationGoal
from kkp.schemas.admin.donations import DonationGoalCreate, DonationGoalUpdate
from kkp.schemas.donations import DonationGoalInfo

router = APIRouter(prefix="/donations", dependencies=[JwtAuthAdminDepN])


@router.post("", response_model=DonationGoalInfo)
async def create_goal(data: DonationGoalCreate):
    goal = await DonationGoal.create(**data.model_dump())
    return goal.to_json()


@router.patch("/{goal_id}", response_model=DonationGoalInfo)
async def update_goal(goal: DonationGoalDep, data: DonationGoalUpdate):
    updates = data.model_dump(exclude_defaults=True)
    if updates:
        await goal.update_from_dict(updates).save(update_fields=list(updates.keys()))

    return goal.to_json()