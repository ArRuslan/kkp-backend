import pytest
from httpx import AsyncClient

from kkp.models import UserRole, Animal, AnimalStatus, AnimalReport, GeoPoint
from kkp.schemas.animal_reports import AnimalReportInfo
from kkp.schemas.common import PaginationResponse
from tests.conftest import create_token, create_user


LON = 42.42424242
LAT = 24.24242424


class PaginatedAnimalReportResponse(PaginationResponse[AnimalReportInfo]):
    ...


@pytest.mark.asyncio
async def test_admin_get_animal_reports_empty(client: AsyncClient):
    token = await create_token(UserRole.GLOBAL_ADMIN)
    response = await client.get("/admin/animal-reports", headers={"authorization": token})
    assert response.status_code == 200, response.json()
    resp = PaginatedAnimalReportResponse(**response.json())
    assert resp.count == 0
    assert len(resp.result) == 0


@pytest.mark.asyncio
async def test_admin_get_animal_reports_pagination_filtering(client: AsyncClient):
    animals = [
        await Animal.create(name=f"test {i}", breed="test idk", status=AnimalStatus.FOUND)
        for i in range(100)
    ]
    reports = [
        await AnimalReport.create(
            animal=animal, location=await GeoPoint.create(latitude=animal.id + .0, longitude=90 - animal.id + .0),
        )
        for animal in animals
    ]
    report_ids = [report.id for report in reports]

    token = await create_token(UserRole.GLOBAL_ADMIN)
    response = await client.get("/admin/animal-reports?page=1&page_size=25", headers={"authorization": token})
    assert response.status_code == 200, response.json()
    resp = PaginatedAnimalReportResponse(**response.json())
    assert resp.count == 100
    assert len(resp.result) == 25
    assert [report.id for report in resp.result] == report_ids[0:25]

    token = await create_token(UserRole.GLOBAL_ADMIN)
    response = await client.get("/admin/animal-reports?page=1&page_size=25&order=desc", headers={"authorization": token})
    assert response.status_code == 200, response.json()
    resp = PaginatedAnimalReportResponse(**response.json())
    assert resp.count == 100
    assert len(resp.result) == 25
    assert [report.id for report in resp.result] == report_ids[:-25-1:-1]


@pytest.mark.asyncio
async def test_admin_get_animal_report(client: AsyncClient):
    report = await AnimalReport.create(
        animal=await Animal.create(name=f"test 123", breed="test idk", status=AnimalStatus.FOUND),
        location=await GeoPoint.create(latitude=LAT, longitude=LON),
    )

    token = await create_token(UserRole.GLOBAL_ADMIN)
    response = await client.get(f"/admin/animal-reports/{report.id}", headers={"authorization": token})
    assert response.status_code == 200, response.json()
    resp = AnimalReportInfo(**response.json())
    assert resp.animal.name == "test 123"
    assert resp.assigned_to is None
    assert resp.reported_by is None


@pytest.mark.asyncio
async def test_admin_edit_animal_report(client: AsyncClient):
    report = await AnimalReport.create(
        animal=await Animal.create(name=f"test 123", breed="test idk", status=AnimalStatus.FOUND),
        location=await GeoPoint.create(latitude=LAT, longitude=LON),
    )

    token = await create_token(UserRole.GLOBAL_ADMIN)
    response = await client.get(f"/admin/animal-reports/{report.id}", headers={"authorization": token})
    assert response.status_code == 200, response.json()
    resp = AnimalReportInfo(**response.json())
    assert resp.animal.name == "test 123"
    assert resp.notes == ""

    response = await client.patch(f"/admin/animal-reports/{report.id}", headers={"authorization": token}, json={
        "notes": "asdqwe 123 test"
    })
    assert response.status_code == 200, response.json()
    resp = AnimalReportInfo(**response.json())
    assert resp.animal.name == "test 123"
    assert resp.notes == "asdqwe 123 test"


@pytest.mark.asyncio
async def test_admin_edit_animal_report_assign_to_user(client: AsyncClient):
    report = await AnimalReport.create(
        animal=await Animal.create(name=f"test 123", breed="test idk", status=AnimalStatus.FOUND),
        location=await GeoPoint.create(latitude=LAT, longitude=LON),
    )

    user = await create_user(UserRole.VET)
    token = await create_token(UserRole.GLOBAL_ADMIN)

    response = await client.get(f"/admin/animal-reports/{report.id}", headers={"authorization": token})
    assert response.status_code == 200, response.json()
    resp = AnimalReportInfo(**response.json())
    assert resp.assigned_to is None

    response = await client.patch(f"/admin/animal-reports/{report.id}", headers={"authorization": token}, json={
        "assigned_to_id": user.id + 100,
    })
    assert response.status_code == 404, response.json()

    response = await client.patch(f"/admin/animal-reports/{report.id}", headers={"authorization": token}, json={
        "assigned_to_id": user.id,
    })
    assert response.status_code == 200, response.json()
    resp = AnimalReportInfo(**response.json())
    assert resp.assigned_to is not None
    assert resp.assigned_to.id == user.id


@pytest.mark.asyncio
async def test_admin_delete_animal_report(client: AsyncClient):
    report = await AnimalReport.create(
        animal=await Animal.create(name=f"test 123", breed="test idk", status=AnimalStatus.FOUND),
        location=await GeoPoint.create(latitude=LAT, longitude=LON),
    )

    token = await create_token(UserRole.GLOBAL_ADMIN)
    response = await client.get(f"/admin/animal-reports/{report.id}", headers={"authorization": token})
    assert response.status_code == 200, response.json()
    assert AnimalReportInfo(**response.json())

    response = await client.delete(f"/admin/animal-reports/{report.id}", headers={"authorization": token})
    assert response.status_code == 204, response.json()

    response = await client.get(f"/admin/animal-reports/{report.id}", headers={"authorization": token})
    assert response.status_code == 404, response.json()
