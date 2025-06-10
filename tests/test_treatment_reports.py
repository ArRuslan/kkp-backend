from asyncio import sleep
from datetime import datetime, UTC, timedelta

import pytest
from httpx import AsyncClient
from pytest_httpx import HTTPXMock

from kkp.models import UserRole, Animal, AnimalReport, GeoPoint, AnimalStatus, PayoutStatus, TreatmentReport
from kkp.schemas.animal_reports import AnimalReportInfo
from kkp.schemas.common import PaginationResponse
from kkp.schemas.treatment_reports import TreatmentReportInfo
from kkp.utils.cache import Cache
from kkp.utils.paypal import PayPal
from tests.conftest import create_token, httpx_mock_decorator
from tests.paypal_mock import PaypalMockState

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
    assert report.payout_status is PayoutStatus.NOT_REQUESTED

    response = await client.get(f"/animal-reports/my", headers={"authorization": vet_token})
    assert response.status_code == 200, response.json()
    reports = PaginationAnimalReportResponse(**response.json())
    assert reports.count == 0
    assert len(reports.result) == 0

    admin_token = await create_token(UserRole.GLOBAL_ADMIN)

    response = await client.post(f"/admin/treatment-reports/{report.id}/payout", headers={"authorization": admin_token})
    assert response.status_code == 400, response.json()


@httpx_mock_decorator
@pytest.mark.asyncio
async def test_treatment_report_payout(client: AsyncClient, httpx_mock: HTTPXMock):
    Cache.disable()
    mock_state = PaypalMockState()
    httpx_mock.add_callback(mock_state.auth_callback, method="POST", url=PayPal.AUTHORIZE)
    httpx_mock.add_callback(mock_state.payout_create_callback, method="POST", url=PayPal.PAYOUTS)
    httpx_mock.add_callback(mock_state.payout_get_callback, method="GET", url=PaypalMockState.GET_PAYOUT_RE)

    admin_token = await create_token(UserRole.GLOBAL_ADMIN)
    vet_token = await create_token(UserRole.VET)

    report = await AnimalReport.create(
        animal=await Animal.create(name=f"test 123", breed="test idk", status=AnimalStatus.FOUND),
        location=await GeoPoint.create(latitude=LAT, longitude=LON),
    )

    response = await client.post(f"/animal-reports/{report.id}/assign", headers={"authorization": vet_token})
    assert response.status_code == 200, response.json()

    response = await client.post("/treatment-reports", headers={"authorization": vet_token}, json={
        "animal_report_id": report.id,
        "description": "test treatment report",
        "money_spent": 123.5,
        "payout_email": "asd@example.com",
    })
    assert response.status_code == 200, response.json()
    treatment_report = TreatmentReportInfo(**response.json())
    assert treatment_report.payout_status is PayoutStatus.REQUESTED

    response = await client.post(f"/admin/treatment-reports/{report.id}/payout", headers={"authorization": admin_token})
    assert response.status_code == 200, response.json()

    response = await client.post(f"/admin/treatment-reports/{report.id}/payout", headers={"authorization": admin_token})
    assert response.status_code == 400, response.json()

    t_report = await TreatmentReport.get(id=treatment_report.id)
    assert t_report.payout_status is PayoutStatus.PENDING

    mock_state.mark_payout_as_completed(t_report.payout_id)

    response = await client.get(f"/treatment-reports/{t_report.id}", headers={"authorization": vet_token})
    assert response.status_code == 200, response.json()
    treatment_report = TreatmentReportInfo(**response.json())
    assert treatment_report.payout_status is PayoutStatus.PENDING  # because of payout_last_checked

    t_report.payout_last_checked = datetime.now(UTC) - timedelta(days=1)
    await t_report.save(update_fields=["payout_last_checked"])

    response = await client.get(f"/treatment-reports/{t_report.id}", headers={"authorization": vet_token})
    assert response.status_code == 200, response.json()
    treatment_report = TreatmentReportInfo(**response.json())
    assert treatment_report.payout_status is PayoutStatus.PENDING  # because check will run AFTER response

    i = 0
    while i < 10:
        await t_report.refresh_from_db()
        if t_report.payout_status is PayoutStatus.COMPLETED:
            break
        i += 1
        await sleep(.5)

    assert t_report.payout_status is PayoutStatus.COMPLETED

    response = await client.get(f"/treatment-reports/{t_report.id}", headers={"authorization": vet_token})
    assert response.status_code == 200, response.json()
    treatment_report = TreatmentReportInfo(**response.json())
    assert treatment_report.payout_status is PayoutStatus.COMPLETED
