from contextlib import asynccontextmanager
from os import environ

import aiocache
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from httpx import RemoteProtocolError
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from tortoise import generate_config
from tortoise.contrib.fastapi import RegisterTortoise

from .config import config, S3, SMTP
from .routes import auth, animals, media, users, subscriptions, animal_reports, admin, messages, treatment_reports, \
    vet_clinics, volunteer_requests, donations
from .utils.custom_exception import CustomMessageException


@asynccontextmanager
async def migrate_and_connect_orm(app_: FastAPI):
    policy_retries = 3
    for i in range(policy_retries):
        try:
            await S3.put_bucket_policy(config.s3_bucket_name, {
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": {"AWS": ["*"]},
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{config.s3_bucket_name}/*"]
                }]
            })
            break
        except RemoteProtocolError:  # pragma: no cover
            if i == policy_retries - 1:
                raise

            from asyncio import sleep
            await sleep(1)

    aiocache.caches.set_config({
        "default": {
            "cache": "aiocache.RedisCache",
            "endpoint": config.redis_host,
            "port": config.redis_port,
            "serializer": {"class": "aiocache.serializers.JsonSerializer"},
            "plugins": [],
        },
    })

    is_testing = environ.get("KKP_TESTING") == "1"
    orm_config = generate_config(
        config.db_connection_string,
        app_modules={"models": ["kkp.models"]},
        testing=is_testing,
    )

    async with RegisterTortoise(
            app=app_,
            config=orm_config,
            generate_schemas=True,
            _create_db=is_testing,
    ), SMTP:
        yield


app = FastAPI(
    lifespan=migrate_and_connect_orm,
    debug=config.is_debug,
    openapi_url="/openapi.json" if config.is_debug else None,
    root_path=config.root_path,
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
app.include_router(admin.router)
app.include_router(animals.router)
app.include_router(media.router)
app.include_router(users.router)
app.include_router(subscriptions.router)
app.include_router(animal_reports.router)
app.include_router(messages.router)
app.include_router(treatment_reports.router)
app.include_router(vet_clinics.router)
app.include_router(volunteer_requests.router)
app.include_router(donations.router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_, exc: RequestValidationError) -> JSONResponse:
    result = []
    for err in exc.errors():
        loc = ".".join([str(l) for l in err["loc"][1:]])
        if loc:
            loc = f"[{loc}] "
        result.append(f"{loc}{err['msg']}")

    return JSONResponse({
        "errors": result,
    }, status_code=422)


@app.exception_handler(CustomMessageException)
async def custom_message_exception_handler(_, exc: CustomMessageException) -> JSONResponse:
    return JSONResponse({
        "errors": exc.messages,
    }, status_code=exc.status_code)
