import pytest
from httpx import AsyncClient

from kkp.models import UserRole
from kkp.schemas.animal_reports import AnimalReportInfo
from kkp.schemas.common import PaginationResponse
from kkp.schemas.treatment_reports import TreatmentReportInfo
from tests.conftest import create_token

LON = 42.42424242
LAT = 24.24242424


class PaginationAnimalReportResponse(PaginationResponse[AnimalReportInfo]):
    ...


@pytest.mark.asyncio
async def test_create_treatment_report(client: AsyncClient):
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
    animal_report = AnimalReportInfo(**response.json())
    report_id = animal_report.id

    response = await client.post(f"/animal-reports/{report_id}/assign", headers={"authorization": vet_token})
    assert response.status_code == 200, response.json()

    response = await client.get(f"/animal-reports/my", headers={"authorization": vet_token})
    assert response.status_code == 200, response.json()
    reports = PaginationAnimalReportResponse(**response.json())
    assert reports.count == 1
    assert reports.result[0].id == report_id

    response = await client.post("/treatment-reports", headers={"authorization": vet_token}, json={
        "animal_report_id": report_id,
        "description": "test treatment report",
        "money_spent": 1234.5,
    })
    assert response.status_code == 200, response.json()
    report = TreatmentReportInfo(**response.json())
    exclude = {"updated_at": True, "assigned_to": True, "animal": {"updated_at": True}}
    assert report.animal_report.model_dump(exclude=exclude) == animal_report.model_dump(exclude=exclude)
    assert report.vet_clinic is None
    assert report.money_spent == 1234.5
    assert report.description == "test treatment report"

    response = await client.get(f"/animal-reports/my", headers={"authorization": vet_token})
    assert response.status_code == 200, response.json()
    reports = PaginationAnimalReportResponse(**response.json())
    assert reports.count == 0
    assert len(reports.result) == 0
