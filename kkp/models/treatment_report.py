from __future__ import annotations

from datetime import datetime

from tortoise import fields, Model

from kkp import models
from kkp.utils.cache import Cache


class TreatmentReport(Model):
    id: int = fields.BigIntField(pk=True)
    report: models.AnimalReport = fields.ForeignKeyField("models.AnimalReport")
    created_at: datetime = fields.DatetimeField(auto_now_add=True)
    description: str = fields.TextField()
    money_spent: float = fields.FloatField()  # ??
    vet_clinic: models.VetClinic | None = fields.ForeignKeyField("models.VetClinic", null=True, default=None)

    @Cache.decorator()
    async def to_json(self) -> dict:
        self.report = await self.report
        if self.vet_clinic is not None:
            self.vet_clinic = await self.vet_clinic

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
