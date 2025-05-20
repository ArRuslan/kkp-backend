from pydantic import BaseModel


class DonationGoalCreate(BaseModel):
    name: str
    description: str
    need_amount: float


class DonationGoalUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    need_amount: float | None = None
    ended_at: int | None = None
