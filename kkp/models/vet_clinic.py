from __future__ import annotations

from tortoise import fields

from kkp import models
from kkp.db.custom_model import CustomModel
from kkp.utils.cache import Cache


class VetClinic(CustomModel):
    id: int = fields.BigIntField(pk=True)
    name: str = fields.CharField(max_length=255)
    location: models.GeoPoint = fields.ForeignKeyField("models.GeoPoint")
    admin: models.User | None = fields.ForeignKeyField("models.User", null=True, related_name="vet_admin")
    employees: fields.ManyToManyRelation[models.User] = fields.ManyToManyField("models.User")

    @Cache.decorator()
    async def to_json(self) -> dict:
        await self.fetch_related_maybe("location", "admin")

        return {
            "id": self.id,
            "name": self.name,
            "location": self.location.to_json(),
            "admin": await self.admin.to_json_base() if self.admin is not None else None,
            "employees_count": await self.employees.all().count(),
        }

    def cache_key(self) -> str:
        return f"vet-clinic-{self.id}"

    cache_ns = cache_key
