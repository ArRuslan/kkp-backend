import pytest
from httpx import AsyncClient
from pydantic import RootModel

from kkp.models import UserRole
from kkp.models.volunteer_request import VolAvailability, VolHelp
from kkp.schemas.volunteer_requests import VolunteerRequestInfo
from tests.conftest import create_token

VolRequestList = RootModel[list[VolunteerRequestInfo]]
VOL_REQUEST_DATA = {
    "full_name": "test 123 asd",
    "text": "some text idk",
    "media_ids": [],
    "has_vehicle": True,
    "phone_number": "+380999999999",
    "city": "test",
    "availability": VolAvailability.WEEKDAYS,
    "help": VolHelp.MEDICAL_CARE | VolHelp.ONSITE_VISIT,
    "telegram_username": "test_username",
    "viber_phone": None,
    "whatsapp_phone": None,
}

@pytest.mark.asyncio
async def test_get_volunteer_requests_empty(client: AsyncClient):
    user_token = await create_token(UserRole.REGULAR)
    response = await client.get("/volunteer-requests", headers={"authorization": user_token})
    assert response.status_code == 200, response.json()
    resp = VolRequestList(response.json())
    assert len(resp.root) == 0


@pytest.mark.asyncio
async def test_send_volunteer_request(client: AsyncClient):
    user_token = await create_token(UserRole.REGULAR)

    response = await client.post(f"/volunteer-requests", headers={"authorization": user_token}, json=VOL_REQUEST_DATA)
    assert response.status_code == 200, response.json()
    vol_request = VolunteerRequestInfo(**response.json())
    assert vol_request.full_name == "test 123 asd"
    assert vol_request.text == "some text idk"
    assert vol_request.medias == []
    assert vol_request.has_vehicle
    assert vol_request.phone_number == "+380999999999"
    assert vol_request.city == "test"
    assert vol_request.availability == VolAvailability.WEEKDAYS
    assert vol_request.help == VolHelp.MEDICAL_CARE | VolHelp.ONSITE_VISIT
    assert vol_request.telegram_username == "test_username"
    assert vol_request.viber_phone is None
    assert vol_request.whatsapp_phone is None

    response = await client.get("/volunteer-requests", headers={"authorization": user_token})
    assert response.status_code == 200, response.json()
    resp = VolRequestList(response.json())
    assert len(resp.root) == 1
    assert resp.root[0] == vol_request

    response = await client.post(f"/volunteer-requests", headers={"authorization": user_token}, json=VOL_REQUEST_DATA)
    assert response.status_code == 400, response.json()


@pytest.mark.asyncio
async def test_send_volunteer_request_already_volunteer(client: AsyncClient):
    user_token = await create_token(UserRole.VOLUNTEER)

    response = await client.post(f"/volunteer-requests", headers={"authorization": user_token}, json=VOL_REQUEST_DATA)
    assert response.status_code == 400, response.json()
