from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from kkp.schemas.common import PaginationQuery
from kkp.schemas.users import UserBaseInfo


class DonationGoalInfo(BaseModel):
    id: int
    name: str
    description: str
    need_amount: float
    got_amount: float
    created_at: int
    ended_at: int | None


class DonationInfo(BaseModel):
    id: int
    user: UserBaseInfo | None
    amount: float
    date: datetime
    comment: str
    goal: DonationGoalInfo


class DonationGoalsQuery(PaginationQuery):
    order: Literal["asc", "desc"] = "asc"
    order_by: Literal["id", "created_at", "ended_at"] = "id"


class GoalDonationsQuery(PaginationQuery):
    order: Literal["asc", "desc"] = "asc"
    order_by: Literal["id", "date"] = "id"


class CreateDonationRequest(BaseModel):
    amount: float
    anonymous: bool
    comment: str = ""


class DonationCreatedInfo(BaseModel):
    id: int
    paypal_id: str
