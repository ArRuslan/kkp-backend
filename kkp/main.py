from contextlib import asynccontextmanager
from pathlib import Path

from aerich import Command
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from tortoise import Tortoise
from tortoise.contrib.fastapi import RegisterTortoise

from .config import config
from .routes import auth
from .utils.custom_exception import CustomMessageException


@asynccontextmanager
async def migrate_and_connect_orm(app_: FastAPI):  # pragma: no cover
    if not config.is_debug:
        migrations_dir = "data/migrations"

        command = Command({
            "connections": {"default": str(config.db_connection_string)},
            "apps": {"models": {"models": ["kkp.models", "aerich.models"], "default_connection": "default"}},
        }, location=migrations_dir)
        await command.init()
        if Path(migrations_dir).exists():
            await command.migrate()
            await command.upgrade(True)
        else:
            await command.init_db(True)
        await Tortoise.close_connections()

    async with RegisterTortoise(
            app=app_,
            db_url=str(config.db_connection_string),
            modules={"models": ["kkp.models"]},
            generate_schemas=True,
    ):
        yield


app = FastAPI(
    lifespan=migrate_and_connect_orm,
    debug=config.is_debug,
    openapi_url="/openapi.json" if config.is_debug else None,
)
app.add_middleware(
    CORSMiddleware,  # type: ignore
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=(["*"] if config.is_debug else [])
)

app.include_router(auth.router)


@app.exception_handler(CustomMessageException)
async def custom_message_exception_handler(_, exc: CustomMessageException) -> JSONResponse:
    return JSONResponse({
        "errors": exc.messages,
    }, status_code=exc.status_code)