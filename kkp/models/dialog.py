from __future__ import annotations

from tortoise import Model, fields

from kkp import models
from kkp.utils.cache import Cache


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

    @Cache.decorator()
    async def to_json(self, current_user: models.User | int, with_last_message: bool = False) -> dict:
        if isinstance(current_user, models.User):
            current_user = current_user.id

        other_user = self.from_user if self.to_user_id == current_user else self.to_user
        other_user = await other_user

        last_message = None
        if with_last_message:
            last = await models.Message.filter(dialog=self).order_by("-id").first()
            if last is not None:
                last_message = {
                    "id": last.id,
                    "text": last.text,
                    "has_media": last.media_id is not None,
                    "date": int(last.date.timestamp()),
                }

        return {
            "id": self.id,
            "user": await other_user.to_json_base(),
            "last_message": last_message,
        }

    def cache_key(self) -> str:
        return f"dialog-{self.id}"

    cache_ns = cache_key
