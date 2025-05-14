import pytest
from httpx import AsyncClient

from kkp.models import UserRole
from kkp.schemas.animal_reports import AnimalReportInfo
from tests.conftest import create_token

LON = 42.42424242
LAT = 24.24242424


@pytest.mark.asyncio
async def test_create_animal_report(client: AsyncClient):
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
