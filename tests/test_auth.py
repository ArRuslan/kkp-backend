from time import time

import pytest
from httpx import AsyncClient
from pytest_httpx import HTTPXMock

from kkp.config import config
from kkp.models import User
from kkp.schemas.auth import GoogleAuthUrlData, ConnectGoogleData, GoogleClientIdData, LoginResponse
from kkp.schemas.users import UserInfo
from kkp.utils.google_id_token import GOOGLE_OAUTH2_CERTS_URL
from kkp.utils.google_oauth import GOOGLE_TOKEN_URL, GOOGLE_USERINFO_URL
from kkp.utils.mfa import Mfa
from tests.conftest import PWD_HASH_123456789, httpx_mock_decorator, get_reset_token
from tests.google_mock import GoogleMockState


@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    response = await client.post("/auth/register", json={
        "email": f"test{time()}@gmail.com",
        "password": "123456789",
        "first_name": "first",
        "last_name": "last",
    })
    assert response.status_code == 200, response.json()
    assert response.json().keys() == {"token", "expires_at"}


@pytest.mark.asyncio
async def test_register_already_registered(client: AsyncClient):
    email = f"test{time()}@gmail.com"
    response = await client.post("/auth/register", json={
        "email": email,
        "password": "123456789",
        "first_name": "first",
        "last_name": "last",
    })
    assert response.status_code == 200, response.json()

    response = await client.post("/auth/register", json={
        "email": email,
        "password": "123456789",
        "first_name": "first",
        "last_name": "last",
    })
    assert response.status_code == 400, response.json()


@pytest.mark.asyncio
async def test_register_invalid_email(client: AsyncClient):
    response = await client.post("/auth/register", json={
        "email": f"test{time()}",
        "password": "123456789",
        "first_name": "first",
        "last_name": "last",
    })
    assert response.status_code == 422, response.json()


@pytest.mark.asyncio
async def test_login(client: AsyncClient):
    email = f"test{time()}@gmail.com"
    response = await client.post("/auth/register", json={
        "email": email,
        "password": "123456789",
        "first_name": "first",
        "last_name": "last",
    })
    assert response.status_code == 200, response.json()

    response = await client.post("/auth/login", json={
        "email": email,
        "password": "123456789",
    })
    assert response.status_code == 200, response.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    email = f"test{time()}@gmail.com"
    response = await client.post("/auth/register", json={
        "email": email,
        "password": "123456789",
        "first_name": "first",
        "last_name": "last",
    })
    assert response.status_code == 200, response.json()

    response = await client.post("/auth/login", json={
        "email": email,
        "password": "123456789qwe",
    })
    assert response.status_code == 400, response.json()


@pytest.mark.asyncio
async def test_login_invalid_email(client: AsyncClient):
    response = await client.post("/auth/login", json={
        "email": f"test{time()}",
        "password": "123456789",
    })
    assert response.status_code == 422, response.json()


@pytest.mark.asyncio
async def test_login_unregistered_email(client: AsyncClient):
    response = await client.post("/auth/login", json={
        "email": f"test{time()}@gmail.com",
        "password": "123456789",
    })
    assert response.status_code == 400, response.json()


@pytest.mark.asyncio
async def test_login_mfa(client: AsyncClient):
    mfa_key = "A" * 16
    user = await User.create(
        email=f"test{time()}@gmail.com", password=PWD_HASH_123456789,
        first_name="first", last_name="last", mfa_key=mfa_key,
    )

    response = await client.post("/auth/login", json={
        "email": user.email,
        "password": "123456789",
    })
    assert response.status_code == 400, response.json()
    resp = response.json()
    assert "mfa_token" in resp

    response = await client.post("/auth/login/mfa", json={
        "mfa_code": Mfa.get_code(mfa_key),
        "mfa_token": resp["mfa_token"],
    })
    assert response.status_code == 200, response.json()
    assert response.json().keys() == {"token", "expires_at"}


@pytest.mark.asyncio
async def test_login_mfa_verify_twice_error(client: AsyncClient):
    mfa_key = "A" * 16
    user = await User.create(
        email=f"test{time()}@gmail.com", password=PWD_HASH_123456789,
        first_name="first", last_name="last", mfa_key=mfa_key,
    )

    response = await client.post("/auth/login", json={
        "email": user.email,
        "password": "123456789",
    })
    assert response.status_code == 400, response.json()
    resp = response.json()
    assert "mfa_token" in resp

    response = await client.post("/auth/login/mfa", json={
        "mfa_code": Mfa.get_code(mfa_key),
        "mfa_token": resp["mfa_token"],
    })
    assert response.status_code == 200, response.json()
    assert response.json().keys() == {"token", "expires_at"}

    response = await client.post("/auth/login/mfa", json={
        "mfa_code": Mfa.get_code(mfa_key),
        "mfa_token": resp["mfa_token"],
    })
    assert response.status_code == 400, response.json()


@pytest.mark.asyncio
async def test_login_mfa_wrong_code(client: AsyncClient):
    mfa_key = "A" * 16
    user = await User.create(
        email=f"test{time()}@gmail.com", password=PWD_HASH_123456789,
        first_name="first", last_name="last", mfa_key=mfa_key,
    )

    response = await client.post("/auth/login", json={
        "email": user.email,
        "password": "123456789",
    })
    assert response.status_code == 400, response.json()
    resp = response.json()
    assert "mfa_token" in resp

    response = await client.post("/auth/login/mfa", json={
        "mfa_code": str((int(Mfa.get_code(mfa_key)) + 1) % 1000000).zfill(6),
        "mfa_token": resp["mfa_token"],
    })
    assert response.status_code == 400, response.json()


@pytest.mark.asyncio
async def test_login_mfa_invalid_token(client: AsyncClient):
    response = await client.post("/auth/login/mfa", json={
        "mfa_code": "111111",
        "mfa_token": "asd.qwe.123",
    })
    assert response.status_code == 400, response.json()


@httpx_mock_decorator
@pytest.mark.asyncio
async def test_register_login_with_google(client: AsyncClient, httpx_mock: HTTPXMock):
    mock_state = GoogleMockState()
    httpx_mock.add_callback(mock_state.token_callback, method="POST", url=GOOGLE_TOKEN_URL)
    httpx_mock.add_callback(mock_state.userinfo_callback, method="GET", url=GOOGLE_USERINFO_URL)

    response = await client.get("/auth/google")
    assert response.status_code == 200, response.json()
    assert GoogleAuthUrlData(**response.json()).url

    code = mock_state.add_user("test@example.com", "test_first", "test_last")

    response = await client.post("/auth/google/callback", json={"code": code})
    assert response.status_code == 200, response.json()
    data = ConnectGoogleData(**response.json())
    assert not data.connect
    assert data.token is not None

    response = await client.post("/auth/google/callback", json={"code": code})
    assert response.status_code == 400, response.json()

    response = await client.get("/user/info", headers={"authorization": data.token})
    assert response.status_code == 200, response.json()
    user_info = UserInfo(**response.json())
    assert user_info.email == "test@example.com"
    assert user_info.first_name == "test_first"
    assert user_info.last_name == "test_last"

    code = mock_state.add_user("test@example.com", "whatever", "whatever")

    response = await client.post("/auth/google/callback", json={"code": code})
    assert response.status_code == 200, response.json()
    new_data = ConnectGoogleData(**response.json())
    assert not new_data.connect
    assert new_data.token is not None

    response = await client.get("/user/info", headers={"authorization": new_data.token})
    assert response.status_code == 200, response.json()
    user_info2 = UserInfo(**response.json())
    assert user_info == user_info2

    response = await client.post("/auth/login", json={
        "email": user_info.email,
        "password": "any-password-is-wrong-because-user-doesnt-have-password",
    })
    assert response.status_code == 400, response.json()


@pytest.mark.asyncio
async def test_reset_password(client: AsyncClient):
    user = await User.create(
        email=f"test{time()}@gmail.com", password=PWD_HASH_123456789, first_name="f", last_name="l",
    )

    response = await client.post("/auth/reset-password/request", json={
        "email": user.email,
    })
    assert response.status_code == 204, response.json()

    reset_token = await get_reset_token(user.email)

    response = await client.post("/auth/reset-password/reset", json={
        "reset_token": reset_token,
        "new_password": "147258369",
    })
    assert response.status_code == 204, response.json()

    response = await client.post("/auth/login", json={
        "email": user.email,
        "password": "147258369",
    })
    assert response.status_code == 200, response.json()


@pytest.mark.asyncio
async def test_reset_password_invalid_token(client: AsyncClient):
    user = await User.create(
        email=f"test{time()}@gmail.com", password=PWD_HASH_123456789, first_name="f", last_name="l",
    )

    response = await client.post("/auth/reset-password/request", json={
        "email": user.email,
    })
    assert response.status_code == 204, response.json()

    reset_token = await get_reset_token(user.email)

    response = await client.post("/auth/reset-password/reset", json={
        "reset_token": reset_token+"A",
        "new_password": "147258369",
    })
    assert response.status_code == 400, response.json()


@pytest.mark.asyncio
async def test_reset_password_user_deleted(client: AsyncClient):
    user = await User.create(
        email=f"test{time()}@gmail.com", password=PWD_HASH_123456789, first_name="f", last_name="l",
    )

    response = await client.post("/auth/reset-password/request", json={
        "email": user.email,
    })
    assert response.status_code == 204, response.json()

    reset_token = await get_reset_token(user.email)

    await user.delete()

    response = await client.post("/auth/reset-password/reset", json={
        "reset_token": reset_token,
        "new_password": "147258369",
    })
    assert response.status_code == 400, response.json()


@httpx_mock_decorator
@pytest.mark.asyncio
async def test_register_login_with_google_id(client: AsyncClient, httpx_mock: HTTPXMock):
    mock_state = GoogleMockState()
    httpx_mock.add_callback(mock_state.certs_callback, method="GET", url=GOOGLE_OAUTH2_CERTS_URL)

    response = await client.get("/auth/google/mobile")
    assert response.status_code == 200, response.json()
    assert GoogleClientIdData(**response.json()).client_id == config.oauth_google_client_id

    test_email = "test@example.com"
    mock_state.add_user(test_email, "test_first", "test_last")
    id_token = mock_state.get_id_token_for_user(test_email)

    response = await client.post("/auth/google/mobile-callback", json={"id_token": id_token})
    assert response.status_code == 200, response.json()
    data = LoginResponse(**response.json())
    assert data.token is not None
    kkp_token = data.token

    response = await client.get("/user/info", headers={"authorization": data.token})
    assert response.status_code == 200, response.json()
    user_info = UserInfo(**response.json())
    assert user_info.email == "test@example.com"
    assert user_info.first_name == "test_first"
    assert user_info.last_name == "test_last"

    response = await client.post("/auth/google/mobile-callback", json={"id_token": id_token})
    assert response.status_code == 200, response.json()
    data = LoginResponse(**response.json())
    assert data.token is not None
    assert data.token != kkp_token

    response = await client.get("/user/info", headers={"authorization": data.token})
    assert response.status_code == 200, response.json()
    user_info = UserInfo(**response.json())
    assert user_info.email == "test@example.com"
    assert user_info.first_name == "test_first"
    assert user_info.last_name == "test_last"

    response = await client.post("/auth/login", json={
        "email": user_info.email,
        "password": "any-password-is-wrong-because-user-doesnt-have-password",
    })
    assert response.status_code == 400, response.json()


@pytest.mark.asyncio
async def test_logout(client: AsyncClient):
    user = await User.create(
        email=f"test{time()}@gmail.com", password=PWD_HASH_123456789, first_name="f", last_name="l",
    )

    response = await client.post("/auth/login", json={
        "email": user.email,
        "password": "123456789",
    })
    assert response.status_code == 200, response.json()
    resp = LoginResponse(**response.json())
    token = resp.token

    response = await client.get("/user/info", headers={"authorization": token})
    assert response.status_code == 200, response.json()

    response = await client.post("/auth/logout", headers={"authorization": token})
    assert response.status_code == 204, response.json()

    response = await client.get("/user/info", headers={"authorization": token})
    assert response.status_code == 401, response.json()

    response = await client.post("/auth/logout", headers={"authorization": token})
    assert response.status_code == 401, response.json()


@httpx_mock_decorator
@pytest.mark.asyncio
async def test_register_login_with_google_id_invalid_signature(client: AsyncClient, httpx_mock: HTTPXMock):
    mock_state = GoogleMockState()
    httpx_mock.add_callback(mock_state.certs_callback, method="GET", url=GOOGLE_OAUTH2_CERTS_URL)

    response = await client.get("/auth/google/mobile")
    assert response.status_code == 200, response.json()
    assert GoogleClientIdData(**response.json()).client_id == config.oauth_google_client_id

    test_email = "test@example.com"
    mock_state.add_user(test_email, "test_first", "test_last")
    id_token = mock_state.get_id_token_for_user(test_email)
    id_token = id_token.split(".")
    id_token[2] = id_token[2][::-1]
    id_token = ".".join(id_token)

    response = await client.post("/auth/google/mobile-callback", json={"id_token": id_token})
    assert response.status_code == 400, response.json()


@httpx_mock_decorator
@pytest.mark.asyncio
async def test_register_login_with_google_id_certs_fail(client: AsyncClient, httpx_mock: HTTPXMock):
    from kkp.utils import google_id_token

    google_id_token._GOOGLE_CERTS = None

    mock_state = GoogleMockState()
    httpx_mock.add_callback(mock_state.certs_callback_fail, method="GET", url=GOOGLE_OAUTH2_CERTS_URL)

    response = await client.get("/auth/google/mobile")
    assert response.status_code == 200, response.json()
    assert GoogleClientIdData(**response.json()).client_id == config.oauth_google_client_id

    test_email = "test@example.com"
    mock_state.add_user(test_email, "test_first", "test_last")
    id_token = mock_state.get_id_token_for_user(test_email)

    response = await client.post("/auth/google/mobile-callback", json={"id_token": id_token})
    assert response.status_code == 400, response.json()


@httpx_mock_decorator
@pytest.mark.asyncio
async def test_register_login_with_google_id_invalid_iss(client: AsyncClient, httpx_mock: HTTPXMock):
    mock_state = GoogleMockState(iss="idk")
    httpx_mock.add_callback(mock_state.certs_callback, method="GET", url=GOOGLE_OAUTH2_CERTS_URL)

    response = await client.get("/auth/google/mobile")
    assert response.status_code == 200, response.json()
    assert GoogleClientIdData(**response.json()).client_id == config.oauth_google_client_id

    test_email = "test@example.com"
    mock_state.add_user(test_email, "test_first", "test_last")
    id_token = mock_state.get_id_token_for_user(test_email)

    response = await client.post("/auth/google/mobile-callback", json={"id_token": id_token})
    assert response.status_code == 400, response.json()


@httpx_mock_decorator
@pytest.mark.asyncio
async def test_register_login_with_google_id_invalid_aud(client: AsyncClient, httpx_mock: HTTPXMock):
    mock_state = GoogleMockState(client_id="invalid-client-id")
    httpx_mock.add_callback(mock_state.certs_callback, method="GET", url=GOOGLE_OAUTH2_CERTS_URL)

    response = await client.get("/auth/google/mobile")
    assert response.status_code == 200, response.json()
    assert GoogleClientIdData(**response.json()).client_id == config.oauth_google_client_id

    test_email = "test@example.com"
    mock_state.add_user(test_email, "test_first", "test_last")
    id_token = mock_state.get_id_token_for_user(test_email)

    response = await client.post("/auth/google/mobile-callback", json={"id_token": id_token})
    assert response.status_code == 400, response.json()
