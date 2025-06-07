from __future__ import annotations

from datetime import datetime

from tortoise import fields

from kkp import models
from kkp.db.custom_model import CustomModel
from kkp.utils.cache import Cache


class TreatmentReport(CustomModel):
    id: int = fields.BigIntField(pk=True)
    report: models.AnimalReport = fields.ForeignKeyField("models.AnimalReport")
    created_at: datetime = fields.DatetimeField(auto_now_add=True)
    description: str = fields.TextField()
    money_spent: float = fields.FloatField()  # ??
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
            "vet_clinic": await self.vet_clinic.to_json() if self.vet_clinic else None,
        }

    def cache_key(self) -> str:
        return f"treatment-report-{self.id}"

    cache_ns = cache_key
