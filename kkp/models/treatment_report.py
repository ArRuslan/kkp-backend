from __future__ import annotations

from datetime import datetime

from tortoise import fields, Model

from kkp import models


class TreatmentReport(Model):
    id: int = fields.BigIntField(pk=True)
    report: models.AnimalReport = fields.ForeignKeyField("models.AnimalReport")
    created_at: datetime = fields.DatetimeField(auto_now_add=True)
    description: str = fields.TextField()
    money_spent: float = fields.FloatField()  # ??
