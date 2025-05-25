from asyncio import get_event_loop
from os import environ
from pathlib import Path

from aerich import Command
from tortoise import Tortoise

from .config import config


async def migrate():  # pragma: no cover
    is_testing = environ.get("TORTOISE_TESTING") == "1"
    if not is_testing:
        command = Command({
            "connections": {"default": config.db_connection_string},
            "apps": {"models": {"models": ["kkp.models", "aerich.models"], "default_connection": "default"}},
        }, location=config.migrations_dir)
        await command.init()
        if Path(config.migrations_dir).exists():
            await command.migrate()
            await command.upgrade(True)
        else:
            await command.init_db(True)
        await Tortoise.close_connections()


if __name__ == "__main__":
    get_event_loop().run_until_complete(migrate())
