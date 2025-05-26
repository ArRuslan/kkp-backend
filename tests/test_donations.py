import pytest
from httpx import AsyncClient
from pytest_httpx import HTTPXMock

from kkp.models import UserRole, DonationGoal
from kkp.schemas.common import PaginationResponse
from kkp.schemas.donations import DonationGoalInfo, DonationInfo, DonationCreatedInfo
from kkp.utils.paypal import PayPal
from tests.conftest import create_token
from tests.paypal_mock import PaypalMockState

httpx_mock_decorator = pytest.mark.httpx_mock(
    assert_all_requests_were_expected=False,
    assert_all_responses_were_requested=False,
    can_send_already_matched_responses=True,
)


class PaginatedGoalsResponse(PaginationResponse[DonationGoalInfo]):
    ...


class PaginatedDonationsResponse(PaginationResponse[DonationInfo]):
    ...


@pytest.mark.asyncio
async def test_get_donation_goals_empty(client: AsyncClient):
    response = await client.get("/donations")
    assert response.status_code == 200, response.json()
    resp = PaginatedGoalsResponse(**response.json())
    assert resp.count == 0
    assert len(resp.result) == 0


@pytest.mark.asyncio
async def test_create_donation_goal(client: AsyncClient):
    admin_token = await create_token(UserRole.GLOBAL_ADMIN)

    response = await client.post("/admin/donations", headers={"authorization": admin_token}, json={
        "name": "test",
        "description": "test goal",
        "need_amount": 1234.5,
    })
    assert response.status_code == 200, response.json()
    goal = DonationGoalInfo(**response.json())
    assert goal.name == "test"
    assert goal.description == "test goal"
    assert goal.need_amount == 1234.5

    response = await client.get("/donations")
    assert response.status_code == 200, response.json()
    resp = PaginatedGoalsResponse(**response.json())
    assert resp.count == 1
    assert len(resp.result) == 1
    assert resp.result[0] == goal

    response = await client.get(f"/donations/{goal.id}/donations")
    assert response.status_code == 200, response.json()
    resp = PaginatedDonationsResponse(**response.json())
    assert resp.count == 0
    assert len(resp.result) == 0


@httpx_mock_decorator
@pytest.mark.asyncio
async def test_create_donation_no_auth(client: AsyncClient, httpx_mock: HTTPXMock):
    mock_state = PaypalMockState()
    httpx_mock.add_callback(mock_state.auth_callback, method="POST", url=PayPal.AUTHORIZE)
    httpx_mock.add_callback(mock_state.order_callback, method="POST", url=PayPal.CHECKOUT)
    httpx_mock.add_callback(mock_state.capture_callback, method="POST", url=PaypalMockState.CAPTURE_RE)

    admin_token = await create_token(UserRole.GLOBAL_ADMIN)

    response = await client.post("/admin/donations", headers={"authorization": admin_token}, json={
        "name": "test",
        "description": "test goal",
        "need_amount": 1234.5,
    })
    assert response.status_code == 200, response.json()
    goal = DonationGoalInfo(**response.json())

    response = await client.post(f"/donations/{goal.id}/donate", json={
        "amount": 123,
        "anonymous": False,
        "comment": "test 123",
    })
    assert response.status_code == 200, response.json()
    donation_created = DonationCreatedInfo(**response.json())

    response = await client.post(f"/donations/{goal.id}/donations/{donation_created.id}")
    assert response.status_code == 400, response.json()

    response = await client.get(f"/donations/{goal.id}/donations")
    assert response.status_code == 200, response.json()
    resp = PaginatedDonationsResponse(**response.json())
    assert resp.count == 0
    assert len(resp.result) == 0

    mock_state.mark_as_payed(donation_created.paypal_id)

    response = await client.post(f"/donations/{goal.id}/donations/{donation_created.id}")
    assert response.status_code == 200, response.json()

    response = await client.get(f"/donations/{goal.id}/donations")
    assert response.status_code == 200, response.json()
    resp = PaginatedDonationsResponse(**response.json())
    assert resp.count == 1
    assert len(resp.result) == 1
    assert resp.result[0].id == donation_created.id
    assert resp.result[0].amount == 123
    assert resp.result[0].comment == "test 123"
    assert resp.result[0].user is None

    response = await client.post(f"/donations/{goal.id}/donations/{donation_created.id}")
    assert response.status_code == 400, response.json()


@httpx_mock_decorator
@pytest.mark.asyncio
async def test_create_donation_auth(client: AsyncClient, httpx_mock: HTTPXMock):
    mock_state = PaypalMockState()
    httpx_mock.add_callback(mock_state.auth_callback, method="POST", url=PayPal.AUTHORIZE)
    httpx_mock.add_callback(mock_state.order_callback, method="POST", url=PayPal.CHECKOUT)
    httpx_mock.add_callback(mock_state.capture_callback, method="POST", url=PaypalMockState.CAPTURE_RE)

    goal = await DonationGoal.create(name="test", description="test goal", need_amount=1234.56)

    user_token = await create_token(UserRole.GLOBAL_ADMIN)

    response = await client.post(f"/donations/{goal.id}/donate", headers={"authorization": user_token}, json={
        "amount": 123,
        "anonymous": False,
        "comment": "test 123",
    })
    assert response.status_code == 200, response.json()
    donation_created = DonationCreatedInfo(**response.json())

    response = await client.get(f"/donations/{goal.id}/donations")
    assert response.status_code == 200, response.json()
    resp = PaginatedDonationsResponse(**response.json())
    assert resp.count == 0

    mock_state.mark_as_payed(donation_created.paypal_id)

    response = await client.post(f"/donations/{goal.id}/donations/{donation_created.id}")
    assert response.status_code == 200, response.json()

    response = await client.get(f"/donations/{goal.id}/donations")
    assert response.status_code == 200, response.json()
    resp = PaginatedDonationsResponse(**response.json())
    assert resp.count == 1
    assert len(resp.result) == 1
    assert resp.result[0].id == donation_created.id
    assert resp.result[0].amount == 123
    assert resp.result[0].comment == "test 123"
    assert resp.result[0].user is not None


@httpx_mock_decorator
@pytest.mark.asyncio
async def test_create_donation_auth_anon(client: AsyncClient, httpx_mock: HTTPXMock):
    mock_state = PaypalMockState()
    httpx_mock.add_callback(mock_state.auth_callback, method="POST", url=PayPal.AUTHORIZE)
    httpx_mock.add_callback(mock_state.order_callback, method="POST", url=PayPal.CHECKOUT)
    httpx_mock.add_callback(mock_state.capture_callback, method="POST", url=PaypalMockState.CAPTURE_RE)

    goal = await DonationGoal.create(name="test", description="test goal", need_amount=1234.56)

    user_token = await create_token(UserRole.GLOBAL_ADMIN)

    response = await client.post(f"/donations/{goal.id}/donate", headers={"authorization": user_token}, json={
        "amount": 123,
        "anonymous": True,
        "comment": "test 123",
    })
    assert response.status_code == 200, response.json()
    donation_created = DonationCreatedInfo(**response.json())

    response = await client.get(f"/donations/{goal.id}/donations")
    assert response.status_code == 200, response.json()
    resp = PaginatedDonationsResponse(**response.json())
    assert resp.count == 0

    mock_state.mark_as_payed(donation_created.paypal_id)

    response = await client.post(f"/donations/{goal.id}/donations/{donation_created.id}")
    assert response.status_code == 200, response.json()

    response = await client.get(f"/donations/{goal.id}/donations")
    assert response.status_code == 200, response.json()
    resp = PaginatedDonationsResponse(**response.json())
    assert resp.count == 1
    assert len(resp.result) == 1
    assert resp.result[0].id == donation_created.id
    assert resp.result[0].amount == 123
    assert resp.result[0].comment == "test 123"
    assert resp.result[0].user is None


@httpx_mock_decorator
@pytest.mark.asyncio
async def test_create_donation_ended_goal(client: AsyncClient, httpx_mock: HTTPXMock):
    mock_state = PaypalMockState()
    httpx_mock.add_callback(mock_state.auth_callback, method="POST", url=PayPal.AUTHORIZE)
    httpx_mock.add_callback(mock_state.order_callback, method="POST", url=PayPal.CHECKOUT)
    httpx_mock.add_callback(mock_state.capture_callback, method="POST", url=PaypalMockState.CAPTURE_RE)

    goal = await DonationGoal.create(name="test", description="test goal", need_amount=1234.56)

    response = await client.post(f"/donations/{goal.id}/donate", json={
        "amount": 10000,
        "anonymous": True,
        "comment": "test 123",
    })
    assert response.status_code == 200, response.json()
    donation_created = DonationCreatedInfo(**response.json())

    mock_state.mark_as_payed(donation_created.paypal_id)

    response = await client.post(f"/donations/{goal.id}/donations/{donation_created.id}")
    assert response.status_code == 200, response.json()

    response = await client.post(f"/donations/{goal.id}/donate", json={
        "amount": 1,
        "anonymous": True,
        "comment": "test 123",
    })
    assert response.status_code == 400, response.json()


