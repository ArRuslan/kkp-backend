from __future__ import annotations

from tortoise import Model, fields

from kkp import models


class Dialog(Model):
    id: int = fields.BigIntField(pk=True)
    from_user: models.User = fields.ForeignKeyField("models.User", related_name="from_user")
    to_user: models.User = fields.ForeignKeyField("models.User", related_name="to_user")

    from_user_id: int
    to_user_id: int

    class Meta:
        unique_together = (
            ("from_user", "to_user"),
        )

    async def to_json(self, current_user: models.User | int) -> dict:
        if isinstance(current_user, models.User):
            current_user = current_user.id

        other_user = self.from_user if self.to_user_id == current_user else self.to_user
        other_user = await other_user

        return {
            "id": self.id,
            "user": await other_user.to_json_base(),
        }
