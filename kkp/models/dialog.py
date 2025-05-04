from __future__ import annotations

from tortoise import Model, fields

from kkp import models


class Dialog(Model):
    id: int = fields.BigIntField(pk=True)
    from_user: models.User = fields.ForeignKeyField("models.User", related_name="from_user")
    to_user: models.User = fields.ForeignKeyField("models.User", related_name="to_user")

    class Meta:
        unique_together = (
            ("from_user", "to_user"),
        )
