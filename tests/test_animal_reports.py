import pytest
from httpx import AsyncClient

from kkp.models import UserRole
from kkp.schemas.animal_reports import AnimalReportInfo
from kkp.schemas.common import PaginationResponse
from tests.conftest import create_token

LON = 42.42424242
LAT = 24.24242424


@pytest.mark.asyncio
async def test_create_animal_report(client: AsyncClient):
    user_token = await create_token(UserRole.REGULAR)

    response = await client.post("/animal-reports", headers={"authorization": user_token}, json={
        "name": "test animal",
        "breed": "idk breed",
        "notes": "some notes\n123",
        "latitude": LAT,
        "longitude": LON,
        "media_ids": [],
    })
    assert response.status_code == 200, response.json()
    resp = AnimalReportInfo(**response.json())
    assert resp.animal is not None
    assert resp.animal.name == "test animal"
    assert resp.animal.breed == "idk breed"
    assert resp.animal.media.count == 0
    assert len(resp.animal.media.result) == 0
    assert resp.assigned_to is None
    assert resp.reported_by is not None
    assert resp.media == []
    assert resp.notes == "some notes\n123"
    assert resp.location.latitude == LAT
    assert resp.location.longitude == LON


@pytest.mark.asyncio
async def test_get_report(client: AsyncClient):
    user_token = await create_token(UserRole.REGULAR)
    user2_token = await create_token(UserRole.REGULAR)
    vet_token = await create_token(UserRole.VET)

    response = await client.post("/animal-reports", headers={"authorization": user_token}, json={
        "name": "test animal",
        "breed": "idk breed",
        "notes": "some notes\n123",
        "latitude": LAT,
        "longitude": LON,
        "media_ids": [],
    })
    assert response.status_code == 200, response.json()
    report = AnimalReportInfo(**response.json())
    report_id = report.id

    response = await client.get(f"/animal-reports/{report_id}", headers={"authorization": user_token})
    assert response.status_code == 200, response.json()
    assert AnimalReportInfo(**response.json()) == report

    response = await client.get(f"/animal-reports/{report_id}", headers={"authorization": vet_token})
    assert response.status_code == 200, response.json()
    assert AnimalReportInfo(**response.json()) == report

    response = await client.get(f"/animal-reports/{report_id}", headers={"authorization": user2_token})
    assert response.status_code == 403, response.json()


class PaginationAnimalReportResponse(PaginationResponse[AnimalReportInfo]):
    pass


@pytest.mark.asyncio
async def test_get_recent_reports(client: AsyncClient):
    user_token = await create_token(UserRole.REGULAR)
    vet_token = await create_token(UserRole.VET)

    response = await client.post("/animal-reports", headers={"authorization": user_token}, json={
        "name": "test animal",
        "breed": "idk breed",
        "notes": "some notes\n123",
        "latitude": LAT,
        "longitude": LON,
        "media_ids": [],
    })
    assert response.status_code == 200, response.json()
    report = AnimalReportInfo(**response.json())

    response = await client.get(f"/animal-reports/recent?lon={LON}&lat={LAT}", headers={"authorization": vet_token})
    assert response.status_code == 200, response.json()
    reports = PaginationAnimalReportResponse(**response.json())
    assert reports.count == 1
    assert reports.result[0] == report


@pytest.mark.asyncio
async def test_assign_report(client: AsyncClient):
    user_token = await create_token(UserRole.REGULAR)
    vet_token = await create_token(UserRole.VET)

    response = await client.post("/animal-reports", headers={"authorization": user_token}, json={
        "name": "test animal",
        "breed": "idk breed",
        "notes": "some notes\n123",
        "latitude": LAT,
        "longitude": LON,
        "media_ids": [],
    })
    assert response.status_code == 200, response.json()
    report = AnimalReportInfo(**response.json())

    response = await client.get(f"/animal-reports/recent?lon={LON}&lat={LAT}", headers={"authorization": vet_token})
    assert response.status_code == 200, response.json()
    reports = PaginationAnimalReportResponse(**response.json())
    assert reports.count == 1
    assert reports.result[0] == report

    response = await client.post(f"/animal-reports/{report.id}/assign", headers={"authorization": vet_token})
    assert response.status_code == 200, response.json()
    report2 = AnimalReportInfo(**response.json())
    assert report2.assigned_to is not None
    assert report2.model_dump(exclude={"assigned_to"}) == report.model_dump(exclude={"assigned_to"})

    response = await client.post(f"/animal-reports/{report.id}/assign", headers={"authorization": vet_token})
    assert response.status_code == 400, response.json()

    response = await client.get(f"/animal-reports/recent?lon={LON}&lat={LAT}", headers={"authorization": vet_token})
    assert response.status_code == 200, response.json()
    reports = PaginationAnimalReportResponse(**response.json())
    assert reports.count == 0
