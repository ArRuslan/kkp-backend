from datetime import datetime
from typing import Literal, cast

from fastapi import APIRouter, Query, BackgroundTasks
from pytz import UTC

from kkp.dependencies import JwtAuthAdminDepN, AdminVolunteerRequestDep
from kkp.models import UserRole, VolRequestStatus, VolunteerRequest, User
from kkp.schemas.admin.volunteer_requests import VolReqPaginationQuery, ApproveRejectVolunteerRequest
from kkp.schemas.common import PaginationResponse
from kkp.schemas.volunteer_requests import VolunteerRequestInfo
from kkp.utils.cache import Cache
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

    Cache.disable()
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
    Cache.disable()
    return await vol_request.to_json()


async def _send_approve_reject_notification(user: User, type_: Literal["approved", "rejected"], comment: str) -> None:
    await send_notification(
        user,
        f"Volunteer request {type_}",
        (
                f"Your volunteer request has been {type_}!\n"
                + (f"Comment: \n{comment}" if comment else "")
        ),
    )


@router.post("/{volunteer_request_id}/approve", response_model=VolunteerRequestInfo)
async def approve_volunteer_request(
        vol_request: AdminVolunteerRequestDep, data: ApproveRejectVolunteerRequest, bg: BackgroundTasks,
):
    if vol_request.user.role < UserRole.VOLUNTEER:
        vol_request.user.role = UserRole.VOLUNTEER
        await vol_request.user.save(update_fields=["role"])

    vol_request.status = VolRequestStatus.APPROVED
    vol_request.review_text = data.text
    vol_request.reviewed_at = datetime.now(UTC)
    await vol_request.save(update_fields=["status", "review_text", "reviewed_at"])
    await Cache.delete_obj(vol_request)

    update_user = []
    if vol_request.user.telegram_username is None and vol_request.telegram_username is not None:
        vol_request.user.telegram_username = vol_request.telegram_username
        update_user.append("telegram_username")
    if vol_request.user.viber_phone is None and vol_request.viber_phone is not None:
        vol_request.user.viber_phone = vol_request.viber_phone
        update_user.append("viber_phone")
    if vol_request.user.whatsapp_phone is None and vol_request.whatsapp_phone is not None:
        vol_request.user.whatsapp_phone = vol_request.whatsapp_phone
        update_user.append("whatsapp_phone")

    if update_user:
        await vol_request.user.save(update_fields=update_user)
        await Cache.delete_obj(vol_request.user)

    bg.add_task(
        _send_approve_reject_notification,
        vol_request.user, cast("approved", Literal["approved"]), vol_request.review_text,
    )

    return await vol_request.to_json()


@router.post("/{volunteer_request_id}/reject", response_model=VolunteerRequestInfo)
async def reject_volunteer_request(
        vol_request: AdminVolunteerRequestDep, data: ApproveRejectVolunteerRequest, bg: BackgroundTasks,
):
    vol_request.status = VolRequestStatus.REFUSED
    vol_request.review_text = data.text
    vol_request.reviewed_at = datetime.now(UTC)
    await vol_request.save(update_fields=["status", "review_text", "reviewed_at"])
    await Cache.delete_obj(vol_request)

    bg.add_task(
        _send_approve_reject_notification,
        vol_request.user, cast("rejected", Literal["rejected"]), vol_request.review_text,
    )

    return await vol_request.to_json()