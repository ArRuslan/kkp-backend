from time import time

import pytest
from httpx import AsyncClient

from kkp.models import User, Session, Media, MediaType, MediaStatus
from kkp.schemas.users import UserInfo
from kkp.utils.mfa import Mfa
from tests.conftest import PWD_HASH_123456789, create_token

IMG_1x1_PIXEL_RED = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010802000000907753"
    "de000000017352474200aece1ce90000000c49444154185763f8cfc000000301"
    "0100632455d30000000049454e44ae426082"
)


@pytest.mark.asyncio
async def test_get_user_info_invalid_token(client: AsyncClient):
    response = await client.get("/user/info", headers={"authorization": "asdqwe"})
    assert response.status_code == 401, response.json()

    response = await client.get("/user/info", headers={"authorization": "as.dq.we"})
    assert response.status_code == 401, response.json()


@pytest.mark.asyncio
async def test_user_enable_mfa(client: AsyncClient):
    mfa_key = "A"*16
    user = await User.create(
        email=f"test{int(time())}@gmail.com", password=PWD_HASH_123456789, first_name="first", last_name="last"
    )
    token = (await Session.create(user=user)).to_jwt()

    response = await client.post("/user/mfa/enable", headers={"authorization": token}, json={
        "password": "123456789",
        "key": mfa_key,
        "code": Mfa.get_code(mfa_key),
    })
    assert response.status_code == 200, response.json()
    assert response.json()["mfa_enabled"]


@pytest.mark.asyncio
async def test_user_disable_mfa(client: AsyncClient):
    mfa_key = "A"*16
    user = await User.create(
        email=f"test{int(time())}@gmail.com", password=PWD_HASH_123456789,
        first_name="first", last_name="last", mfa_key=mfa_key,
    )
    token = (await Session.create(user=user)).to_jwt()

    response = await client.post("/user/mfa/disable", headers={"authorization": token}, json={
        "password": "123456789",
        "code": Mfa.get_code(mfa_key),
    })
    assert response.status_code == 200, response.json()
    assert not response.json()["mfa_enabled"]


@pytest.mark.asyncio
async def test_user_enable_mfa_errors(client: AsyncClient):
    mfa_key = "A"*16
    user = await User.create(
        email=f"test{int(time())}@gmail.com", password=PWD_HASH_123456789, first_name="first", last_name="last"
    )
    token = (await Session.create(user=user)).to_jwt()

    response = await client.post("/user/mfa/enable", headers={"authorization": token}, json={
        "password": "123456789",
        "key": mfa_key,
        "code": str(int(Mfa.get_code(mfa_key)) + 1).zfill(6)[-6:],
    })
    assert response.status_code == 400, response.json()  # Wrong code

    response = await client.post("/user/mfa/enable", headers={"authorization": token}, json={
        "password": "123456789",
        "key": mfa_key + "B",
        "code": "000000",
    })
    assert response.status_code == 422, response.json()  # Invalid key

    response = await client.post("/user/mfa/enable", headers={"authorization": token}, json={
        "password": "123456789",
        "key": "1" * 16,
        "code": "000000",
    })
    assert response.status_code == 422, response.json()  # Invalid key (not base32)

    response = await client.post("/user/mfa/enable", headers={"authorization": token}, json={
        "password": "wrong_password",
        "key": mfa_key,
        "code": Mfa.get_code(mfa_key),
    })
    assert response.status_code == 400, response.json()  # Wrong password

    user.mfa_key = mfa_key
    await user.save()

    response = await client.post("/user/mfa/enable", headers={"authorization": token}, json={
        "password": "123456789",
        "key": mfa_key,
        "code": Mfa.get_code(mfa_key),
    })
    assert response.status_code == 400, response.json()  # Already enabled


@pytest.mark.asyncio
async def test_user_disable_mfa_errors(client: AsyncClient):
    mfa_key = "A"*16
    user = await User.create(
        email=f"test{int(time())}@gmail.com", password=PWD_HASH_123456789,
        first_name="first", last_name="last", mfa_key=mfa_key,
    )
    token = (await Session.create(user=user)).to_jwt()

    response = await client.post("/user/mfa/disable", headers={"authorization": token}, json={
        "password": "wrong_password",
        "code": Mfa.get_code(mfa_key),
    })
    assert response.status_code == 400, response.json()  # Wrong password

    response = await client.post("/user/mfa/disable", headers={"authorization": token}, json={
        "password": "wrong_password",
        "code": str(int(Mfa.get_code(mfa_key)) + 1).zfill(6)[-6:],
    })
    assert response.status_code == 400, response.json()  # Wrong code

    user.mfa_key = None
    await user.save()

    response = await client.post("/user/mfa/disable", headers={"authorization": token}, json={
        "password": "123456789",
        "code": Mfa.get_code(mfa_key),
    })
    assert response.status_code == 400, response.json()  # Not enabled


@pytest.mark.asyncio
async def test_register_unregister_fcm(client: AsyncClient):
    user = await User.create(
        email=f"test{int(time())}@gmail.com", password=PWD_HASH_123456789, first_name="first", last_name="last",
    )
    session = await Session.create(user=user)
    token = session.to_jwt()

    assert session.fcm_token is None

    response = await client.post("/user/register-device", headers={"authorization": token}, json={
        "fcm_token": "some-fcm-token-123456",
    })
    assert response.status_code == 204, response.json()
    await session.refresh_from_db()
    assert session.fcm_token == "some-fcm-token-123456"

    response = await client.post("/user/unregister-device", headers={"authorization": token})
    assert response.status_code == 204, response.json()
    await session.refresh_from_db()
    assert session.fcm_token is None


@pytest.mark.asyncio
async def test_change_password(client: AsyncClient):
    user = await User.create(
        email=f"test{int(time())}@gmail.com", password=PWD_HASH_123456789, first_name="first", last_name="last",
    )
    session = await Session.create(user=user)
    token = session.to_jwt()

    response = await client.post("/auth/login", json={
        "email": user.email,
        "password": "123456789",
    })
    assert response.status_code == 200, response.json()

    response = await client.patch("/user/password", headers={"authorization": token}, json={
        "old_password": "123456789",
        "new_password": "987654321",
    })
    assert response.status_code == 200, response.json()

    response = await client.post("/auth/login", json={
        "email": user.email,
        "password": "123456789",
    })
    assert response.status_code == 400, response.json()

    response = await client.post("/auth/login", json={
        "email": user.email,
        "password": "987654321",
    })
    assert response.status_code == 200, response.json()


@pytest.mark.asyncio
async def test_edit_user(client: AsyncClient):
    token = await create_token()
    session = await Session.from_jwt(token)
    media = await Media.create(uploaded_by=session.user, type=MediaType.PHOTO, status=MediaStatus.UPLOADED)

    response = await client.patch("/user/info", headers={"authorization": token}, json={
        "first_name": "updated_first_name",
        "last_name": "updated_last_name",
        "email": "updated_email@example.com",
        "photo_id": media.id,
        "telegram_username": "updated_telegram_username",
        "viber_phone": "+380991111111",
        "whatsapp_phone": "+380999999999",
    })
    assert response.status_code == 200, response.json()
    resp = UserInfo(**response.json())
    assert resp.first_name == "updated_first_name"
    assert resp.last_name == "updated_last_name"
    assert resp.email == "updated_email@example.com"
    assert resp.photo is not None
    assert resp.photo.id == media.id
    assert resp.telegram_username == "updated_telegram_username"
    assert resp.viber_phone == "+380991111111"
    assert resp.whatsapp_phone == "+380999999999"


@pytest.mark.asyncio
async def test_edit_user_remove_photo(client: AsyncClient):
    token = await create_token()
    session = await Session.from_jwt(token)
    media = await Media.create(uploaded_by=session.user, type=MediaType.PHOTO, status=MediaStatus.UPLOADED)

    response = await client.patch("/user/info", headers={"authorization": token}, json={
        "photo_id": media.id,
    })
    assert response.status_code == 200, response.json()
    resp = UserInfo(**response.json())
    assert resp.photo is not None
    assert resp.photo.id == media.id

    response = await client.patch("/user/info", headers={"authorization": token}, json={
        "photo_id": 0,
    })
    assert response.status_code == 200, response.json()
    resp = UserInfo(**response.json())
    assert resp.photo is None


@pytest.mark.asyncio
async def test_edit_user_invalid_photo(client: AsyncClient):
    token = await create_token()
    session = await Session.from_jwt(token)
    media = await Media.create(uploaded_by=session.user, type=MediaType.PHOTO, status=MediaStatus.UPLOADED)

    response = await client.patch("/user/info", headers={"authorization": token}, json={
        "photo_id": media.id+100,
    })
    assert response.status_code == 400, response.json()

    response = await client.get("/user/info", headers={"authorization": token})
    assert response.status_code == 200, response.json()
    resp = UserInfo(**response.json())
    assert resp.photo is None


@pytest.mark.asyncio
async def test_edit_user_occupied_email(client: AsyncClient):
    token = await create_token()
    other_user = await User.create(email=f"test_used@gmail.com", password="", first_name="a", last_name="b")

    response = await client.get("/user/info", headers={"authorization": token})
    assert response.status_code == 200, response.json()
    resp = UserInfo(**response.json())
    old_email = resp.email

    response = await client.patch("/user/info", headers={"authorization": token}, json={
        "email": other_user.email,
    })
    assert response.status_code == 400, response.json()

    response = await client.get("/user/info", headers={"authorization": token})
    assert response.status_code == 200, response.json()
    resp = UserInfo(**response.json())
    assert resp.email == old_email


@pytest.mark.asyncio
async def test_change_password_wrong_old(client: AsyncClient):
    user = await User.create(
        email=f"test{int(time())}@gmail.com", password=PWD_HASH_123456789, first_name="first", last_name="last",
    )
    session = await Session.create(user=user)
    token = session.to_jwt()

    response = await client.patch("/user/password", headers={"authorization": token}, json={
        "old_password": "123456788",
        "new_password": "987654321",
    })
    assert response.status_code == 400, response.json()

    response = await client.post("/auth/login", json={
        "email": user.email,
        "password": "123456789",
    })
    assert response.status_code == 200, response.json()


@pytest.mark.asyncio
async def test_update_location(client: AsyncClient):
    user = await User.create(
        email=f"test{int(time())}@gmail.com", password=PWD_HASH_123456789, first_name="first", last_name="last",
    )
    session = await Session.create(user=user)
    token = session.to_jwt()

    assert session.location.lat == 0
    assert session.location.lon == 0

    response = await client.post("/user/location", headers={"authorization": token}, json={
        "latitude": 12.34,
        "longitude": 56.78,
    })
    assert response.status_code == 204, response.json()
    await session.refresh_from_db()
    assert session.location.lat == 12.34
    assert session.location.lon == 56.78
