from datetime import datetime

from fastapi import APIRouter, Query
from pytz import UTC

from kkp.dependencies import JwtAuthAdminDepN, AdminVolunteerRequestDep
from kkp.models import UserRole, VolRequestStatus, VolunteerRequest
from kkp.schemas.admin.volunteer_requests import VolReqPaginationQuery, ApproveRejectVolunteerRequest
from kkp.schemas.common import PaginationResponse
from kkp.schemas.volunteer_requests import VolunteerRequestInfo
from kkp.utils.notification_util import send_notification

router = APIRouter(prefix="/volunteer-requests", dependencies=[JwtAuthAdminDepN])


@router.get("", response_model=PaginationResponse[VolunteerRequestInfo])
async def get_volunteer_requests(query: VolReqPaginationQuery = Query()):
    req_query = VolunteerRequest.filter()

    if query.id is not None:
        req_query = req_query.filter(id=query.id)
    if query.status is not None:
        req_query = req_query.filter(status=query.status)
    if query.user_id is not None:
        req_query = req_query.filter(user__id=query.user_id)

    order = query.order_by
    if query.order == "desc":
        order = f"-{order}"

    req_query = req_query.order_by(order)

    return {
        "count": await req_query.count(),
        "result": [
            await req.to_json()
            for req in await req_query.select_related("user") \
                .limit(query.page_size) \
                .offset(query.page_size * (query.page - 1))
        ],
    }


@router.get("/{volunteer_request_id}", response_model=VolunteerRequestInfo)
async def get_volunteer_request(vol_request: AdminVolunteerRequestDep):
    return await vol_request.to_json()


@router.post("/{volunteer_request_id}/approve", response_model=VolunteerRequestInfo)
async def approve_volunteer_request(vol_request: AdminVolunteerRequestDep, data: ApproveRejectVolunteerRequest):
    if vol_request.user.role < UserRole.VOLUNTEER:
        vol_request.user.role = UserRole.VOLUNTEER
        await vol_request.user.save(update_fields=["role"])

    vol_request.status = VolRequestStatus.APPROVED
    vol_request.review_text = data.text
    vol_request.reviewed_at = datetime.now(UTC)
    await vol_request.save(update_fields=["status", "review_text", "reviewed_at"])

    await send_notification(
        vol_request.user,
        "Volunteer request approved",
        (
            f"Your volunteer request has been approved!\n"
            +(f"Comment: \n{vol_request.review_text}" if vol_request.review_text else "")
        ),
    )

    return await vol_request.to_json()


@router.post("/{volunteer_request_id}/reject", response_model=VolunteerRequestInfo)
async def reject_volunteer_request(vol_request: AdminVolunteerRequestDep, data: ApproveRejectVolunteerRequest):
    vol_request.status = VolRequestStatus.REFUSED
    vol_request.review_text = data.text
    vol_request.reviewed_at = datetime.now(UTC)
    await vol_request.save(update_fields=["status", "review_text", "reviewed_at"])

    await send_notification(
        vol_request.user,
        "Volunteer request rejected",
        (
                f"Your volunteer request has been rejected!\n"
                + (f"Comment: \n{vol_request.review_text}" if vol_request.review_text else "")
        ),
    )

    return await vol_request.to_json()