from typing import Literal

from kkp.models import PayoutStatus
from kkp.schemas.common import PaginationQuery


class ReportsQuery(PaginationQuery):
    order: Literal["asc", "desc"] = "asc"
    order_by: Literal["id", "created_at", "money_spent", "payout_status"] = "id"
    id: int | None = None
    report_id: int | None = None
    payout_status: PayoutStatus | None = None
