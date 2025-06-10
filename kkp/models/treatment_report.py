from __future__ import annotations

from datetime import datetime
from enum import IntEnum

from tortoise import fields

from kkp import models
from kkp.db.custom_model import CustomModel
from kkp.utils.cache import Cache


class PayoutStatus(IntEnum):
    NOT_REQUESTED = 0
    REQUESTED = 1
    PENDING = 2
    COMPLETED = 3


class TreatmentReport(CustomModel):
    id: int = fields.BigIntField(pk=True)
    report: models.AnimalReport = fields.ForeignKeyField("models.AnimalReport")
    created_at: datetime = fields.DatetimeField(auto_now_add=True)
    description: str = fields.TextField()
    money_spent: float = fields.FloatField()
    payout_email: str | None = fields.CharField(max_length=256, null=True, default=None)
    payout_status: PayoutStatus = fields.IntEnumField(PayoutStatus, default=PayoutStatus.NOT_REQUESTED)
    payout_id: str | None = fields.CharField(max_length=64, null=True, default=None)
    payout_last_checked: datetime = fields.DatetimeField(null=True, default=None)
    vet_clinic: models.VetClinic | None = fields.ForeignKeyField("models.VetClinic", null=True, default=None)

    @Cache.decorator()
    async def to_json(self) -> dict:
        await self.fetch_related_maybe("report", "vet_clinic")

        return {
            "id": self.id,
            "animal_report": await self.report.to_json(),
            "created_at": int(self.created_at.timestamp()),
            "description": self.description,
            "money_spent": self.money_spent,
            "payout_status": self.payout_status,
            "vet_clinic": await self.vet_clinic.to_json() if self.vet_clinic else None,
        }

    def cache_key(self) -> str:
        return f"treatment-report-{self.id}"

    cache_ns = cache_key
