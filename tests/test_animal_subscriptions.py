import pytest
from httpx import AsyncClient

from kkp.models import UserRole, Animal, AnimalStatus
from kkp.schemas.animals import AnimalInfo
from kkp.schemas.common import PaginationResponse
from tests.conftest import create_token


class AnimalPaginationResponse(PaginationResponse[AnimalInfo]):
    ...


@pytest.mark.asyncio
async def test_get_subscriptions_empty(client: AsyncClient):
    user_token = await create_token(UserRole.REGULAR)

    response = await client.get("/subscriptions", headers={"authorization": user_token})
    assert response.status_code == 200, response.json()
    resp = AnimalPaginationResponse(**response.json())
    assert resp.count == 0
    assert len(resp.result) == 0


@pytest.mark.asyncio
async def test_subscribe_to_animal(client: AsyncClient):
    user_token = await create_token(UserRole.REGULAR)
    animal = await Animal.create(name="test animal", breed="some breed", status=AnimalStatus.FOUND)

    response = await client.get("/subscriptions", headers={"authorization": user_token})
    assert response.status_code == 200, response.json()
    resp = AnimalPaginationResponse(**response.json())
    assert resp.count == 0
    assert len(resp.result) == 0

    for _ in range(2):
        response = await client.put(f"/subscriptions/{animal.id}", headers={"authorization": user_token})
        assert response.status_code == 204, response.json()

    response = await client.get("/subscriptions", headers={"authorization": user_token})
    assert response.status_code == 200, response.json()
    resp = AnimalPaginationResponse(**response.json())
    assert resp.count == 1
    assert len(resp.result) == 1
    assert resp.result[0].id == animal.id


@pytest.mark.asyncio
async def test_unsubscribe_from_animal(client: AsyncClient):
    user_token = await create_token(UserRole.REGULAR)
    animal = await Animal.create(name="test animal", breed="some breed", status=AnimalStatus.FOUND)

    response = await client.get("/subscriptions", headers={"authorization": user_token})
    assert response.status_code == 200, response.json()
    resp = AnimalPaginationResponse(**response.json())
    assert resp.count == 0
    assert len(resp.result) == 0

    for _ in range(2):
        response = await client.put(f"/subscriptions/{animal.id}", headers={"authorization": user_token})
        assert response.status_code == 204, response.json()

    response = await client.get("/subscriptions", headers={"authorization": user_token})
    assert response.status_code == 200, response.json()
    resp = AnimalPaginationResponse(**response.json())
    assert resp.count == 1
    assert len(resp.result) == 1
    assert resp.result[0].id == animal.id

    for _ in range(2):
        response = await client.delete(f"/subscriptions/{animal.id}", headers={"authorization": user_token})
        assert response.status_code == 204, response.json()

    response = await client.get("/subscriptions", headers={"authorization": user_token})
    assert response.status_code == 200, response.json()
    resp = AnimalPaginationResponse(**response.json())
    assert resp.count == 0
    assert len(resp.result) == 0


@pytest.mark.asyncio
async def test_subscribe_to_unknown_animal(client: AsyncClient):
    user_token = await create_token(UserRole.REGULAR)
    animal = await Animal.create(name="test animal", breed="some breed", status=AnimalStatus.FOUND)

    response = await client.put(f"/subscriptions/{animal.id + 100}", headers={"authorization": user_token})
    assert response.status_code == 404, response.json()

    response = await client.get("/subscriptions", headers={"authorization": user_token})
    assert response.status_code == 200, response.json()
    resp = AnimalPaginationResponse(**response.json())
    assert resp.count == 0
    assert len(resp.result) == 0
