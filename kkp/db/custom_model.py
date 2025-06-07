from inspect import isawaitable

from tortoise import Model


class CustomModel(Model):
    async def fetch_related_maybe(self, *fields_to_fetch: str) -> None:
        to_fetch = []
        for field_name in fields_to_fetch:
            field = getattr(self, field_name)
            if not isawaitable(field):
                continue
            if not field or isinstance(field, Model):
                setattr(self, field_name, await field)
            else:
                to_fetch.append(field_name)

        if to_fetch:
            await self.fetch_related(*to_fetch)
