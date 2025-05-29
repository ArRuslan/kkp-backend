import pytest
from httpx import AsyncClient

from kkp.models import UserRole, Session, MediaStatus, MediaType, Media
from kkp.schemas.common import PaginationResponse
from kkp.schemas.messages import DialogInfo, MessageInfo
from tests.conftest import create_token, create_user


class DialogPaginationResponse(PaginationResponse[DialogInfo]):
    ...


class MessagePaginationResponse(PaginationResponse[MessageInfo]):
    ...


@pytest.mark.asyncio
async def test_list_dialogs_empty(client: AsyncClient):
    user_token = await create_token(UserRole.REGULAR)

    response = await client.get("/messages", headers={"authorization": user_token})
    assert response.status_code == 200, response.json()
    resp = DialogPaginationResponse(**response.json())
    assert resp.count == 0
    assert len(resp.result) == 0


@pytest.mark.asyncio
async def test_get_messages_in_nonexistent_dialog_empty(client: AsyncClient):
    user1 = await create_user(UserRole.REGULAR)
    session1 = await Session.create(user=user1)
    user_token1 =  session1.to_jwt()

    response = await client.get(f"/messages/{user1.id}", headers={"authorization": user_token1})
    assert response.status_code == 200, response.json()
    resp = MessagePaginationResponse(**response.json())
    assert resp.count == 0
    assert len(resp.result) == 0


@pytest.mark.asyncio
async def test_send_message_to_self(client: AsyncClient):
    user1 = await create_user(UserRole.REGULAR)
    session1 = await Session.create(user=user1)
    user_token1 = session1.to_jwt()

    response = await client.get(f"/messages/{user1.id}", headers={"authorization": user_token1})
    assert response.status_code == 200, response.json()
    resp = MessagePaginationResponse(**response.json())
    assert resp.count == 0
    assert len(resp.result) == 0

    response = await client.post(f"/messages/{user1.id}", headers={"authorization": user_token1}, json={
        "text": "123 test",
    })
    assert response.status_code == 200, response.json()
    message_resp = MessageInfo(**response.json())
    assert message_resp.text == "123 test"
    assert message_resp.media is None
    assert message_resp.author.id == user1.id
    assert message_resp.dialog.user.id == user1.id

    response = await client.get(f"/messages/{user1.id}", headers={"authorization": user_token1})
    assert response.status_code == 200, response.json()
    resp = MessagePaginationResponse(**response.json())
    assert resp.count == 1
    assert len(resp.result) == 1
    assert resp.result[0] == message_resp


@pytest.mark.asyncio
async def test_send_message_to_other_user(client: AsyncClient):
    user1 = await create_user(UserRole.REGULAR)
    session1 = await Session.create(user=user1)
    user_token1 = session1.to_jwt()
    user2 = await create_user(UserRole.REGULAR)
    session2 = await Session.create(user=user2)
    user_token2 = session2.to_jwt()

    response = await client.get(f"/messages/{user2.id}", headers={"authorization": user_token1})
    assert response.status_code == 200, response.json()
    resp = MessagePaginationResponse(**response.json())
    assert resp.count == 0
    assert len(resp.result) == 0

    response = await client.get(f"/messages/{user1.id}", headers={"authorization": user_token2})
    assert response.status_code == 200, response.json()
    resp = MessagePaginationResponse(**response.json())
    assert resp.count == 0
    assert len(resp.result) == 0

    response = await client.post(f"/messages/{user2.id}", headers={"authorization": user_token1}, json={
        "text": "123 test",
    })
    assert response.status_code == 200, response.json()
    message_resp = MessageInfo(**response.json())
    assert message_resp.text == "123 test"
    assert message_resp.media is None
    assert message_resp.author.id == user1.id
    assert message_resp.dialog.user.id == user2.id

    response = await client.get("/messages", headers={"authorization": user_token1})
    assert response.status_code == 200, response.json()
    resp = DialogPaginationResponse(**response.json())
    assert resp.count == 1
    assert len(resp.result) == 1
    assert resp.result[0].last_message is not None
    assert resp.result[0].last_message.id == message_resp.id
    assert resp.result[0].last_message.text == message_resp.text
    assert not resp.result[0].last_message.has_media

    response = await client.get(f"/messages/{user2.id}", headers={"authorization": user_token1})
    assert response.status_code == 200, response.json()
    resp = MessagePaginationResponse(**response.json())
    assert resp.count == 1
    assert len(resp.result) == 1
    assert resp.result[0] == message_resp

    response = await client.get(f"/messages/{user1.id}", headers={"authorization": user_token2})
    assert response.status_code == 200, response.json()
    resp = MessagePaginationResponse(**response.json())
    assert resp.count == 1
    assert len(resp.result) == 1
    assert resp.result[0].text == message_resp.text
    assert resp.result[0].author == message_resp.author
    assert resp.result[0].dialog.user.id == user1.id


@pytest.mark.asyncio
async def test_send_message_to_other_user_with_media(client: AsyncClient):
    user1 = await create_user(UserRole.REGULAR)
    session1 = await Session.create(user=user1)
    user_token1 = session1.to_jwt()
    user2 = await create_user(UserRole.REGULAR)
    session2 = await Session.create(user=user2)
    user_token2 = session2.to_jwt()

    media = await Media.create(uploaded_by=user1, status=MediaStatus.UPLOADED, type=MediaType.PHOTO)

    response = await client.post(f"/messages/{user2.id}", headers={"authorization": user_token1}, json={
        "text": "",
        "media_id": media.id,
    })
    assert response.status_code == 200, response.json()
    message_resp = MessageInfo(**response.json())
    assert message_resp.text == ""
    assert message_resp.media is not None
    assert message_resp.media.id == media.id
    assert message_resp.author.id == user1.id
    assert message_resp.dialog.user.id == user2.id

    response = await client.get("/messages", headers={"authorization": user_token1})
    assert response.status_code == 200, response.json()
    resp = DialogPaginationResponse(**response.json())
    assert resp.count == 1
    assert len(resp.result) == 1
    assert resp.result[0].last_message is not None
    assert resp.result[0].last_message.id == message_resp.id
    assert resp.result[0].last_message.text == message_resp.text
    assert resp.result[0].last_message.has_media

    response = await client.get(f"/messages/{user2.id}", headers={"authorization": user_token1})
    assert response.status_code == 200, response.json()
    resp = MessagePaginationResponse(**response.json())
    assert resp.count == 1
    assert len(resp.result) == 1
    assert resp.result[0] == message_resp

    response = await client.get(f"/messages/{user1.id}", headers={"authorization": user_token2})
    assert response.status_code == 200, response.json()
    resp = MessagePaginationResponse(**response.json())
    assert resp.count == 1
    assert len(resp.result) == 1
    assert resp.result[0].text == message_resp.text
    assert resp.result[0].author == message_resp.author
    assert resp.result[0].dialog.user.id == user1.id
