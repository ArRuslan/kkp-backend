from __future__ import annotations

from datetime import datetime
from enum import IntEnum

from tortoise import fields, Model

from kkp import models


class AnimalUpdateType(IntEnum):
    ANIMAL = 1
    REPORT = 2
    TREATMENT = 3


class AnimalUpdate(Model):
    id: int = fields.BigIntField(pk=True)
    animal: models.Animal = fields.ForeignKeyField("models.Animal")
    date: datetime = fields.DatetimeField(auto_now_add=True)
    type: AnimalUpdateType = fields.IntEnumField(AnimalUpdateType)
    animal_report: models.AnimalReport | None = fields.ForeignKeyField("models.AnimalReport", null=True, default=None)
    treatment_report: models.TreatmentReport | None = fields.ForeignKeyField("models.TreatmentReport", null=True, default=None)

    async def to_json(self) -> dict:
        self.animal = await self.animal

        if self.type is AnimalUpdateType.REPORT and self.animal_report is not None:
            self.animal_report = await self.animal_report
        if self.type is AnimalUpdateType.TREATMENT and self.treatment_report is not None:
            self.treatment_report = await self.treatment_report

        return {
            "id": self.id,
            "animal": await self.animal.to_json(),
            "type": self.type,
            "date": int(self.date.timestamp()),
            "animal_report": await self.animal_report.to_json() if self.type is AnimalUpdateType.REPORT and self.animal_report is not None else None,
            "treatment_report": await self.treatment_report.to_json() if self.type is AnimalUpdateType.TREATMENT and self.treatment_report is not None else None,
        }
