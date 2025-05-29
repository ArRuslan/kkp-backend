import pytest
from httpx import AsyncClient

from kkp.models import UserRole, MediaType
from kkp.schemas.animal_reports import AnimalReportInfo
from kkp.schemas.common import PaginationResponse
from kkp.schemas.media import CreateMediaUploadResponse, MediaInfo
from tests.conftest import create_token
from tests.test_media import IMG_1x1_PIXEL_RED

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

    response = await client.get(f"/animal-reports/my", headers={"authorization": vet_token})
    assert response.status_code == 200, response.json()
    reports = PaginationAnimalReportResponse(**response.json())
    assert reports.count == 1
    assert reports.result[0] == report2


@pytest.mark.asyncio
async def test_create_report_for_existing_animal(client: AsyncClient):
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

    response = await client.get(f"/animals/{report.animal.id}/reports", headers={"authorization": vet_token})
    assert response.status_code == 200, response.json()
    reports = PaginationAnimalReportResponse(**response.json())
    assert reports.count == 1
    assert reports.result[0] == report

    response = await client.post("/animal-reports", headers={"authorization": user_token}, json={
        "animal_id": report.animal.id,
        "breed": "i can put here whatever i want",
        "notes": "some notes\n123",
        "latitude": LAT,
        "longitude": LON,
        "media_ids": [],
    })
    assert response.status_code == 200, response.json()
    report2 = AnimalReportInfo(**response.json())

    assert report2.animal == report.animal

    response = await client.get(f"/animals/{report.animal.id}/reports", headers={"authorization": vet_token})
    assert response.status_code == 200, response.json()
    reports = PaginationAnimalReportResponse(**response.json())
    assert reports.count == 2


@pytest.mark.asyncio
async def test_create_report_for_nonexisting_animal(client: AsyncClient):
    user_token = await create_token(UserRole.REGULAR)

    response = await client.post("/animal-reports", headers={"authorization": user_token}, json={
        "animal_id": 123456,
        "notes": "some notes\n123",
        "latitude": LAT,
        "longitude": LON,
        "media_ids": [],
    })
    assert response.status_code == 404, response.json()


@pytest.mark.asyncio
async def test_create_report_without_name_and_id(client: AsyncClient):
    user_token = await create_token(UserRole.REGULAR)

    response = await client.post("/animal-reports", headers={"authorization": user_token}, json={
        "notes": "some notes\n123",
        "latitude": LAT,
        "longitude": LON,
        "media_ids": [],
    })
    assert response.status_code == 400, response.json()


@pytest.mark.asyncio
async def test_create_animal_report_no_auth(client: AsyncClient):
    response = await client.post("/animal-reports", json={
        "name": "test animal 1",
        "breed": "idk breed 1",
        "notes": "some notes\n123",
        "latitude": LAT,
        "longitude": LON,
        "media_ids": [],
    })
    assert response.status_code == 200, response.json()
    report = AnimalReportInfo(**response.json())
    assert report.animal is not None
    assert report.animal.name == "test animal 1"
    assert report.animal.breed == "idk breed 1"
    assert report.animal.media.count == 0
    assert len(report.animal.media.result) == 0
    assert report.assigned_to is None
    assert report.reported_by is None
    assert report.media == []
    assert report.notes == "some notes\n123"
    assert report.location.latitude == LAT
    assert report.location.longitude == LON

    response = await client.get(f"/animal-reports/{report.id}")
    assert response.status_code == 200, response.json()
    assert AnimalReportInfo(**response.json()) == report


@pytest.mark.asyncio
async def test_create_animal_report_no_auth_media(client: AsyncClient):
    response = await client.post("/media", json={
        "type": MediaType.PHOTO.value,
        "size": len(IMG_1x1_PIXEL_RED),
    })
    assert response.status_code == 200, response.json()
    resp = CreateMediaUploadResponse(**response.json())
    media_id = resp.id

    async with AsyncClient() as cl:
        upload_response = await cl.put(resp.upload_url, content=IMG_1x1_PIXEL_RED)
        assert upload_response.status_code == 200

    response = await client.post(f"/media/{media_id}/finalize")
    assert response.status_code == 200, response.json()
    resp = MediaInfo(**response.json())

    async with AsyncClient() as cl:
        media_response = await cl.get(resp.url)
        assert media_response.status_code == 200
        assert await media_response.aread() == IMG_1x1_PIXEL_RED

    response = await client.post("/animal-reports", json={
        "name": "test animal 1",
        "breed": "idk breed 1",
        "notes": "some notes\n123",
        "latitude": LAT,
        "longitude": LON,
        "media_ids": [media_id],
    })
    assert response.status_code == 200, response.json()
    resp = AnimalReportInfo(**response.json())
    assert resp.animal is not None
    assert resp.animal.name == "test animal 1"
    assert resp.animal.breed == "idk breed 1"
    assert len(resp.media) == 1
    assert resp.media[0].id == media_id
    assert resp.assigned_to is None
    assert resp.reported_by is None
    assert resp.notes == "some notes\n123"
    assert resp.location.latitude == LAT
    assert resp.location.longitude == LON
    assert resp.animal.media.count == 1
    assert len(resp.animal.media.result) == 1
    assert resp.animal.media.result[0].id == media_id
