from __future__ import annotations

from tortoise import Model, fields

from kkp import models
from kkp.utils.cache import Cache


class VetClinic(Model):
    id: int = fields.BigIntField(pk=True)
    name: str = fields.CharField(max_length=255)
    location: models.GeoPoint = fields.ForeignKeyField("models.GeoPoint")
    admin: models.User | None = fields.ForeignKeyField("models.User", null=True, related_name="vet_admin")  # make non nullable??
    employees: fields.ManyToManyRelation[models.User] = fields.ManyToManyField("models.User")

    @Cache.decorator()
    async def to_json(self) -> dict:
        self.location = await self.location
        if self.admin is not None:
            self.admin = await self.admin

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
