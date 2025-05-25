import pytest
from httpx import AsyncClient

from kkp.models import UserRole, Animal, AnimalStatus, AnimalUpdateType
from kkp.schemas.animal_reports import AnimalReportInfo
from kkp.schemas.animal_updates import AnimalUpdateInfo
from kkp.schemas.animals import AnimalInfo
from kkp.schemas.common import PaginationResponse
from kkp.schemas.treatment_reports import TreatmentReportInfo
from tests.conftest import create_token


LON = 42.42424242
LAT = 24.24242424


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


class UpdatePaginationResponse(PaginationResponse[AnimalUpdateInfo]):
    ...


@pytest.mark.asyncio
async def test_subscriptions_updates(client: AsyncClient):
    user_token = await create_token(UserRole.REGULAR)
    vet_token = await create_token(UserRole.VET)
    animal = await Animal.create(name="test animal", breed="some breed", status=AnimalStatus.FOUND)

    response = await client.put(f"/subscriptions/{animal.id}", headers={"authorization": user_token})
    assert response.status_code == 204, response.json()

    response = await client.get("/subscriptions", headers={"authorization": user_token})
    assert response.status_code == 200, response.json()
    resp = AnimalPaginationResponse(**response.json())
    assert resp.count == 1
    assert len(resp.result) == 1
    assert resp.result[0].id == animal.id

    response = await client.post("/animal-reports", headers={"authorization": user_token}, json={
        "animal_id": animal.id,
        "notes": "some notes\n123",
        "latitude": LAT,
        "longitude": LON,
        "media_ids": [],
    })
    assert response.status_code == 200, response.json()
    report = AnimalReportInfo(**response.json())
    report_id = report.id

    response = await client.get("/subscriptions/updates", headers={"authorization": user_token})
    assert response.status_code == 200, response.json()
    resp = UpdatePaginationResponse(**response.json())
    assert resp.count == 1
    assert len(resp.result) == 1
    assert resp.result[0].type == AnimalUpdateType.REPORT
    assert resp.result[0].animal.id == animal.id
    assert resp.result[0].animal_report is not None
    assert resp.result[0].treatment_report is None
    assert resp.result[0].animal_report.id == report_id

    response = await client.post(f"/animal-reports/{report_id}/assign", headers={"authorization": vet_token})
    assert response.status_code == 200, response.json()

    response = await client.post("/treatment-reports", headers={"authorization": vet_token}, json={
        "animal_report_id": report_id,
        "description": "test treatment report",
        "money_spent": 1234.5,
    })
    assert response.status_code == 200, response.json()
    resp = TreatmentReportInfo(**response.json())
    treatment_id = resp.id

    response = await client.get("/subscriptions/updates", headers={"authorization": user_token})
    assert response.status_code == 200, response.json()
    resp = UpdatePaginationResponse(**response.json())
    assert resp.count == 2
    assert len(resp.result) == 2
    assert resp.result[0].type == AnimalUpdateType.TREATMENT
    assert resp.result[0].animal.id == animal.id
    assert resp.result[0].animal_report is None
    assert resp.result[0].treatment_report is not None
    assert resp.result[0].treatment_report.id == treatment_id
    assert resp.result[1].type == AnimalUpdateType.REPORT
    assert resp.result[1].animal.id == animal.id
    assert resp.result[1].animal_report is not None
    assert resp.result[1].treatment_report is None
    assert resp.result[1].animal_report.id == report_id
