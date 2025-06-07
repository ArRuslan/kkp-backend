from __future__ import annotations

from datetime import datetime
from enum import IntEnum, IntFlag

from tortoise import fields

from kkp import models
from kkp.db.custom_model import CustomModel
from kkp.db.int_flag import IntFlagField
from kkp.utils.cache import Cache


class VolRequestStatus(IntEnum):
    REQUESTED = 1
    APPROVED = 2
    REFUSED = 3


class VolAvailability(IntFlag):
    WEEKDAYS = 1 << 0
    WEEKENDS = 1 << 1


class VolHelp(IntFlag):
    SHELTER = 1 << 0
    CLINIC_DELIVERY = 1 << 1
    ONSITE_VISIT = 1 << 2
    MEDICAL_CARE = 1 << 3
    INFORMATION = 1 << 4


class VolunteerRequest(CustomModel):
    id: int = fields.BigIntField(pk=True)
    user: models.User = fields.ForeignKeyField("models.User")
    created_at: datetime = fields.DatetimeField(auto_now_add=True)
    reviewed_at: datetime | None = fields.DatetimeField(null=True, default=None)
    text: str = fields.TextField()
    review_text: str | None = fields.TextField(null=True, default=None)
    medias: fields.ManyToManyRelation[models.Media] = fields.ManyToManyField("models.Media")
    status: VolRequestStatus = fields.IntEnumField(VolRequestStatus, default=VolRequestStatus.REQUESTED)
    full_name: str = fields.CharField(max_length=128)
    has_vehicle: bool = fields.BooleanField()
    phone_number: str = fields.CharField(max_length=64)
    city: str = fields.CharField(max_length=128)
    availability: VolAvailability = IntFlagField(VolAvailability)
    help: VolHelp = IntFlagField(VolHelp)
    telegram_username: str | None = fields.CharField(max_length=128, null=True, default=None)
    viber_phone: str | None = fields.CharField(max_length=64, null=True, default=None)
    whatsapp_phone: str | None = fields.CharField(max_length=64, null=True, default=None)

    @Cache.decorator()
    async def to_json(self) -> dict:
        await self.fetch_related_maybe("user")

        return {
            "id": self.id,
            "user": await self.user.to_json_base(),
            "created_at": int(self.created_at.timestamp()),
            "reviewed_at": int(self.reviewed_at.timestamp()) if self.reviewed_at is not None else None,
            "text": self.text,
            "review_text": self.review_text,
            "medias": [
                media.to_json()
                for media in await self.medias.filter().limit(10)
            ],
            "status": self.status,
            "full_name": self.full_name,
            "has_vehicle": self.has_vehicle,
            "phone_number": self.phone_number,
            "city": self.city,
            "availability": self.availability,
            "help": self.help,
            "telegram_username": self.telegram_username,
            "viber_phone": self.viber_phone,
            "whatsapp_phone": self.whatsapp_phone,
        }

    def cache_key(self) -> str:
        return f"vol-request-{self.id}"

    cache_ns = cache_key
