import re
from asyncio import sleep
from os import environ, urandom
from time import time
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from aiodocker import Docker, DockerError
from asgi_lifespan import LifespanManager
from bcrypt import gensalt, hashpw
from fastapi import FastAPI
from httpx import AsyncClient, RemoteProtocolError, ASGITransport
from pydantic import BaseModel, RootModel

REUSE_TEST_CONTAINERS = True

MINIO_PORT = 55001
MINIO_ENDPOINT = f"http://127.0.0.1:{MINIO_PORT}"
MINIO_CRED = "minioadmin"

MARIADB_PORT = 55002
MARIADB_USER = "kkp"
MARIADB_PASS = "123456789"
MARIADB_DB = "kkp"

SMTP_PORT = 55003
MAILCATCHER_PORT = 55004
REDIS_PORT = 55005

environ["s3_endpoint"] = MINIO_ENDPOINT
environ["s3_access_key_id"] = MINIO_CRED
environ["s3_access_secret_key"] = MINIO_CRED
environ["db_connection_string"] = f"mysql://root:{MARIADB_PASS}@127.0.0.1:{MARIADB_PORT}/{MARIADB_DB}_{{}}"
environ["smtp_port"] = str(SMTP_PORT)
environ["redis_port"] = str(REDIS_PORT)
environ["KKP_TESTING"] = "1"

from kkp.main import app
from kkp.models import UserRole, User, Session


PWD_HASH_123456789 = hashpw(b"123456789", gensalt(4)).decode("utf8")

httpx_mock_decorator = pytest.mark.httpx_mock(
    assert_all_requests_were_expected=False,
    assert_all_responses_were_requested=False,
    can_send_already_matched_responses=True,
)


@pytest_asyncio.fixture
async def app_with_lifespan() -> AsyncGenerator[FastAPI, None]:
    docker = Docker()
    redis_container = await docker.containers.get("kkp-test-redis")
    ready_exec = await redis_container.exec(["redis-cli", "flushall"])
    ready_stream = ready_exec.start()
    while (out_message := await ready_stream.read_out()) is not None:
        if out_message.stream == 1 and b"OK\n" in out_message.data:
            break

    async with LifespanManager(app) as manager:
        yield manager.app

    from kkp.utils.cache import Cache
    await Cache._cache.close()


@pytest_asyncio.fixture
async def client(app_with_lifespan) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app_with_lifespan), base_url="https://kkp.local") as client:
        yield client


async def create_user(role: UserRole = UserRole.REGULAR) -> User:
    rand = int.from_bytes(urandom(6), "big")
    user = await User.create(
        email=f"test{int(time()*1000)}_{rand}@gmail.com", password="", first_name="first", last_name="last", role=role,
    )
    return user


async def create_token(user_role: UserRole = UserRole.REGULAR) -> str:
    session = await Session.create(user=await create_user(user_role))
    return session.to_jwt()


def check_sorted(it: list[int]):
    for i in range(1, len(it)):
        if it[i] < it[i - 1]:
            return False

    return True


async def _get_container(docker: Docker, name: str):
    try:
        container = await docker.containers.get(name)
    except DockerError as e:
        if e.status != 404:
            raise
    else:
        if not REUSE_TEST_CONTAINERS:
            await container.delete(force=True, v=True)
            return None
        else:
            info = await container.show()
            if not info["State"]["Running"]:
                await container.restart()
            return container

    return None


@pytest_asyncio.fixture(scope="session", autouse=True)
async def run_minio_in_docker():
    print("Starting minio container...")
    start_time = time()

    docker = Docker()

    container = await _get_container(docker, "kkp-test-minio")
    if container is None:
        container = await docker.containers.run(name="kkp-test-minio", config={
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
                },
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

    if not REUSE_TEST_CONTAINERS:
        await container.delete(force=True, v=True)
    await docker.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def run_mariadb_in_docker():
    print("Starting mariadb container...")
    start_time = time()

    docker = Docker()

    container = await _get_container(docker, "kkp-test-mariadb")
    if container is None:
        container = await docker.containers.run(name="kkp-test-mariadb", config={
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
                },
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

    if not REUSE_TEST_CONTAINERS:
        await container.delete(force=True, v=True)
    await docker.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def run_mailcatcher_in_docker():
    print("Starting mailcatcher container...")
    start_time = time()

    docker = Docker()

    container = await _get_container(docker, "kkp-test-mailcatcher")
    if container is None:
        container = await docker.containers.run(name="kkp-test-mailcatcher", config={
            "Image": "schickling/mailcatcher:latest",
            "HostConfig": {
                "AutoRemove": True,
                "Memory": 64 * 1024 * 1024,
                "PortBindings": {
                    "1025/tcp": [{"HostPort": f"{SMTP_PORT}"}],
                    "1080/tcp": [{"HostPort": f"{MAILCATCHER_PORT}"}],
                }
            },
        })

    async with AsyncClient() as cl:
        while True:
            try:
                resp = await cl.head(f"http://127.0.0.1:{MAILCATCHER_PORT}/messages")
            except RemoteProtocolError:
                continue
            if resp.status_code == 200:
                break

    print(f"Mailcatcher container is ready in {time() - start_time:.2f} seconds")

    yield

    if not REUSE_TEST_CONTAINERS:
        await container.delete(force=True, v=True)
    await docker.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def run_redis_in_docker():
    print("Starting redis container...")
    start_time = time()

    docker = Docker()

    container = await _get_container(docker, "kkp-test-redis")
    if container is None:
        container = await docker.containers.run(name="kkp-test-redis", config={
            "Image": "redis:latest",
            "HostConfig": {
                "AutoRemove": True,
                "Memory": 64 * 1024 * 1024,
                "PortBindings": {
                    "6379/tcp": [{"HostPort": f"{REDIS_PORT}"}],
                }
            },
        })

    ready = False
    while not ready:
        ready_exec = await container.exec(["redis-cli", "ping"])
        ready_stream = ready_exec.start()
        while (out_message := await ready_stream.read_out()) is not None:
            if out_message.stream == 1 and b"PONG\n" in out_message.data:
                ready = True
                break

    print(f"Redis container is ready in {time() - start_time:.2f} seconds")

    yield

    if not REUSE_TEST_CONTAINERS:
        await container.delete(force=True, v=True)
    await docker.close()


class MailCatcherEmailMetadata(BaseModel):
    id: int
    sender: str
    recipients: list[str]
    subject: str
    size: int
    created_at: str


MailCatcherEmailMetadataList = RootModel[list[MailCatcherEmailMetadata]]
RESET_LINK_RE = re.compile(r'reset-password\?reset_token=([a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+)\b')


async def get_reset_token(user_email: str) -> str:
    async with AsyncClient() as cl:
        email_id = None

        for _ in range(5):
            resp = await cl.get(f"http://127.0.0.1:{MAILCATCHER_PORT}/messages")
            emails = MailCatcherEmailMetadataList(resp.json())
            if not emails.root:
                await sleep(.5)
                continue

            for email in emails.root:
                if email_id is not None:
                    break

                for recipient in email.recipients:
                    if recipient == f"<{user_email}>":
                        email_id = email.id

            if email_id is not None:
                break

            await sleep(.5)

        assert email_id is not None

        resp = await cl.get(f"http://127.0.0.1:{MAILCATCHER_PORT}/messages/{email_id}.plain")
        reset_tokens = RESET_LINK_RE.findall(resp.text)
        assert reset_tokens

    return reset_tokens[0]
