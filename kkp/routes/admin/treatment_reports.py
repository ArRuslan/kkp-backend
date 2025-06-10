from datetime import datetime

from fastapi import APIRouter, Query, BackgroundTasks
from pytz import UTC

from kkp.dependencies import JwtAuthAdminDepN, AdminTreatmentReportDep
from kkp.models import TreatmentReport, PayoutStatus
from kkp.schemas.admin.treatment_reports import ReportsQuery
from kkp.schemas.common import PaginationResponse
from kkp.schemas.treatment_reports import TreatmentReportInfo
from kkp.utils.cache import Cache
from kkp.utils.custom_exception import CustomMessageException
from kkp.utils.notification_util import send_notification
from kkp.utils.payouts import check_payout_maybe
from kkp.utils.paypal import PayPal

router = APIRouter(prefix="/treatment-reports", dependencies=[JwtAuthAdminDepN])


@router.get("", response_model=PaginationResponse[TreatmentReportInfo])
async def get_treatment_reports(bg: BackgroundTasks, query: ReportsQuery = Query()):
    reports_query = TreatmentReport.filter()

    if query.id is not None:
        reports_query = reports_query.filter(id=query.id)
    if query.report_id is not None:
        reports_query = reports_query.filter(report__id=query.report_id)

    order = query.order_by
    if query.order == "desc":
        order = f"-{order}"

    reports_query = reports_query.order_by(order)

    reports_count = await reports_query.count()
    reports = await reports_query.limit(query.page_size).offset(query.page_size * (query.page - 1))
    reports_json = []

    Cache.disable()
    for report in reports:
        reports_json.append(await report.to_json())
        check_payout_maybe(bg, report)

    return {
        "count": reports_count,
        "result": reports_json,
    }


@router.get("/{treatment_report_id}", response_model=TreatmentReportInfo)
async def get_treatment_report(report: AdminTreatmentReportDep, bg: BackgroundTasks):
    check_payout_maybe(bg, report)

    Cache.disable()
    return await report.to_json()


@router.delete("/{treatment_report_id}", status_code=204)
async def delete_animal_report(report: AdminTreatmentReportDep):
    await Cache.delete_obj(report)
    await report.delete()


@router.post("/{treatment_report_id}/payout", response_model=TreatmentReportInfo)
async def create_treatment_report_payout(report: AdminTreatmentReportDep):
    if report.payout_status is PayoutStatus.NOT_REQUESTED:
        raise CustomMessageException("User did not request payout for this treatment report")
    if report.payout_status in (PayoutStatus.PENDING, PayoutStatus.COMPLETED):
        raise CustomMessageException("Payout already approved for this treatment report")

    report.payout_id = await PayPal.create_payout(report.id, report.payout_email, report.money_spent)
    report.payout_status = PayoutStatus.PENDING
    report.payout_last_checked = datetime.now(UTC)
    await report.save(update_fields=["payout_id", "payout_status", "payout_last_checked"])

    await send_notification(
        await report.report.assigned_to,
        "Payout approved",
        "Payout for animal treatment report was approved",
    )

    Cache.disable()
    return await report.to_json()