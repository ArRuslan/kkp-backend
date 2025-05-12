from os import environ
from time import time
from typing import AsyncGenerator

import pytest_asyncio
from aiodocker import Docker
from asgi_lifespan import LifespanManager
from bcrypt import gensalt, hashpw
from fastapi import FastAPI
from httpx import AsyncClient, RemoteProtocolError, ASGITransport
from tortoise import Tortoise

MINIO_PORT = 55001
MINIO_ENDPOINT = f"http://127.0.0.1:{MINIO_PORT}"
MINIO_CRED = "minioadmin"

MARIADB_PORT = 55002
MARIADB_USER = "kkp"
MARIADB_PASS = "123456789"
MARIADB_DB = "kkp"

environ["s3_endpoint"] = MINIO_ENDPOINT
environ["s3_access_key_id"] = MINIO_CRED
environ["s3_access_secret_key"] = MINIO_CRED
environ["db_connection_string"] = f"mysql://{MARIADB_USER}:{MARIADB_PASS}@127.0.0.1:{MARIADB_PORT}/{MARIADB_DB}"
environ["TORTOISE_TEST_DROP_TABLES"] = "1"

from kkp.main import app
from kkp.models import UserRole, User, Session


PWD_HASH_123456789 = hashpw(b"123456789", gensalt(4)).decode("utf8")


@pytest_asyncio.fixture
async def app_with_lifespan() -> AsyncGenerator[FastAPI, None]:
    async with LifespanManager(app) as manager:
        yield manager.app


@pytest_asyncio.fixture
async def client(app_with_lifespan) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app_with_lifespan), base_url="https://kkp.local") as client:
        yield client


async def create_user(role: UserRole = UserRole.REGULAR) -> User:
    user = await User.create(
        email=f"test{time()}@gmail.com", password="", first_name="first", last_name="last", role=role,
    )
    return user


async def create_token(user_role: UserRole = UserRole.REGULAR) -> str:
    session = await Session.create(user=await create_user(user_role))
    return session.to_jwt()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def run_minio_in_docker():
    print("Starting minio container...")
    start_time = time()

    docker = Docker()
    container = await docker.containers.run({
        "Image": "bitnami/minio:2024",
        "Env": [
            "MINIO_ROOT_USER=minioadmin",
            "MINIO_ROOT_PASSWORD=minioadmin",
            "MINIO_SERVER_ACCESS_KEY=minioadmin",
            "MINIO_SERVER_SECRET_KEY=minioadmin",
            "MINIO_DEFAULT_BUCKETS=kkp",
        ],
        "HostConfig": {
            "AutoRemove": True,
            "CapDrop": ["ALL"],
            "Memory": 1024 * 1024 * 1024,
            "SecurityOpt": ["no-new-privileges"],
            "PortBindings": {
                "9000/tcp": [{
                    "HostPort": f"{MINIO_PORT}",
                }],
            }
        },
    })

    async with AsyncClient() as cl:
        while True:
            try:
                resp = await cl.head(f"{MINIO_ENDPOINT}/minio/health/live")
            except RemoteProtocolError:
                continue
            if resp.status_code == 200:
                break

    ready = False
    while not ready:
        ready_exec = await container.exec(["mc", "ready", "local"])
        ready_stream = ready_exec.start()
        while (out_message := await ready_stream.read_out()) is not None:
            if out_message.stream == 1 and b"is ready\n" in out_message.data:
                ready = True
                break

    from s3lite import Client
    s3 = Client(MINIO_CRED, MINIO_CRED, MINIO_ENDPOINT)
    await s3.create_bucket("kkp")
    del s3, Client

    print(f"Minio container is ready in {time() - start_time:.2f} seconds")

    yield

    await container.delete(force=True)
    await docker.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def run_mariadb_in_docker():
    print("Starting mariadb container...")
    start_time = time()

    docker = Docker()
    container = await docker.containers.run({
        "Image": "mariadb:10.6",
        "Env": [
            f"MARIADB_ROOT_PASSWORD={MARIADB_PASS}",
            f"MARIADB_DATABASE={MARIADB_DB}",
            f"MARIADB_USER={MARIADB_USER}",
            f"MARIADB_PASSWORD={MARIADB_PASS}",
        ],
        "HostConfig": {
            "AutoRemove": True,
            "Memory": 128 * 1024 * 1024,
            "PortBindings": {
                "3306/tcp": [{
                    "HostPort": f"{MARIADB_PORT}",
                }],
            }
        },
    })

    while True:
        ping_exec = await container.exec([f"mysqladmin", "ping", "--host=127.0.0.1", f"--password={MARIADB_PASS}", "--silent"])
        ping_stream = ping_exec.start()
        while await ping_stream.read_out() is not None:
            pass
        status = await ping_exec.inspect()
        if status["ExitCode"] == 0:
            break

    print(f"Mariadb container is ready in {time() - start_time:.2f} seconds")

    yield

    await container.delete(force=True)
    await docker.close()
