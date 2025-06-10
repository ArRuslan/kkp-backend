from datetime import datetime, timedelta

from fastapi import BackgroundTasks
from loguru import logger
from pytz import UTC

from kkp.models import TreatmentReport, PayoutStatus
from kkp.utils.custom_exception import CustomMessageException
from kkp.utils.paypal import PayPal


async def check_payout_task(report: TreatmentReport) -> None:
    try:
        payout_completed = await PayPal.check_payout(report.payout_id)
    except CustomMessageException as e:
        logger.opt(exception=e).warning("Failed to check payout status")
        return

    report.payout_last_checked = datetime.now(UTC)

    if not payout_completed:
        await report.save(update_fields=["payout_last_checked"])
        return

    report.payout_status = PayoutStatus.COMPLETED
    await report.save(update_fields=["payout_last_checked", "payout_status"])


def check_payout_maybe(bg: BackgroundTasks, report: TreatmentReport) -> None:
    if report.payout_status is PayoutStatus.PENDING \
            and report.payout_id is not None \
            and report.payout_last_checked is not None \
            and (datetime.now(UTC) - report.payout_last_checked) > timedelta(minutes=30):
        bg.add_task(check_payout_task, report)
