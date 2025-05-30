import pytest
from httpx import AsyncClient

from kkp.models import UserRole, Session, VetClinic, GeoPoint
from kkp.schemas.common import PaginationResponse
from kkp.schemas.users import UserInfo
from kkp.schemas.vet_clinics import VetClinicInfo
from tests.conftest import create_token

LON = 42.42424242
LAT = 24.24242424


class PaginatedClinicsResponse(PaginationResponse[VetClinicInfo]):
    ...


class PaginatedUsersResponse(PaginationResponse[UserInfo]):
    ...


@pytest.mark.asyncio
async def test_get_vet_clinics(client: AsyncClient):
    admin_token = await create_token(UserRole.GLOBAL_ADMIN)
    vet_admin_token = await create_token(UserRole.VET_ADMIN)

    response = await client.get("/admin/vet-clinic", headers={"authorization": admin_token})
    assert response.status_code == 200, response.json()
    resp = PaginatedClinicsResponse(**response.json())
    assert resp.count == 0
    assert len(resp.result) == 0

    response = await client.get("/admin/vet-clinic", headers={"authorization": vet_admin_token})
    assert response.status_code == 200, response.json()
    resp = PaginatedClinicsResponse(**response.json())
    assert resp.count == 0
    assert len(resp.result) == 0


@pytest.mark.asyncio
async def test_create_vet_clinic(client: AsyncClient):
    admin_token = await create_token(UserRole.GLOBAL_ADMIN)
    vet_admin_token = await create_token(UserRole.VET_ADMIN)
    vet_session = await Session.from_jwt(vet_admin_token)

    response = await client.post("/admin/vet-clinic", headers={"authorization": admin_token}, json={
        "name": "test1",
        "latitude": LAT,
        "longitude": LON,
        "admin_id": None,
    })
    assert response.status_code == 200, response.json()
    clinic1 = VetClinicInfo(**response.json())
    assert clinic1.name == "test1"
    assert clinic1.location.latitude == LAT
    assert clinic1.location.longitude == LON
    assert clinic1.admin is None
    assert clinic1.employees_count == 0

    response = await client.post("/admin/vet-clinic", headers={"authorization": admin_token}, json={
        "name": "test2",
        "latitude": LON,
        "longitude": LAT,
        "admin_id": vet_session.user.id,
    })
    assert response.status_code == 200, response.json()
    clinic2 = VetClinicInfo(**response.json())
    assert clinic2.name == "test2"
    assert clinic2.location.latitude == LON
    assert clinic2.location.longitude == LAT
    assert clinic2.admin is not None
    assert clinic2.employees_count == 0

    response = await client.get("/admin/vet-clinic", headers={"authorization": admin_token})
    assert response.status_code == 200, response.json()
    resp = PaginatedClinicsResponse(**response.json())
    assert resp.count == 2
    assert len(resp.result) == 2
    assert (resp.result == [clinic1, clinic2]) or (resp.result == [clinic2, clinic1])

    response = await client.get("/admin/vet-clinic", headers={"authorization": vet_admin_token})
    assert response.status_code == 200, response.json()
    resp = PaginatedClinicsResponse(**response.json())
    assert resp.count == 1
    assert len(resp.result) == 1
    assert resp.result[0] == clinic2

    response = await client.get("/vet-clinic/near", params={"lat": LAT, "lon": LON})
    assert response.status_code == 200, response.json()
    resp = PaginatedClinicsResponse(**response.json())
    assert resp.count == 1
    assert len(resp.result) == 1
    assert resp.result[0] == clinic1

    response = await client.get("/vet-clinic/near", params={"lat": LON, "lon": LAT})
    assert response.status_code == 200, response.json()
    resp = PaginatedClinicsResponse(**response.json())
    assert resp.count == 1
    assert len(resp.result) == 1
    assert resp.result[0] == clinic2


@pytest.mark.asyncio
async def test_get_vet_clinic(client: AsyncClient):
    admin_token = await create_token(UserRole.GLOBAL_ADMIN)
    vet_admin_token = await create_token(UserRole.VET_ADMIN)
    vet_session = await Session.from_jwt(vet_admin_token)

    response = await client.post("/admin/vet-clinic", headers={"authorization": admin_token}, json={
        "name": "test1",
        "latitude": LAT,
        "longitude": LON,
        "admin_id": None,
    })
    assert response.status_code == 200, response.json()
    clinic1 = VetClinicInfo(**response.json())

    response = await client.post("/admin/vet-clinic", headers={"authorization": admin_token}, json={
        "name": "test2",
        "latitude": LON,
        "longitude": LAT,
        "admin_id": vet_session.user.id,
    })
    assert response.status_code == 200, response.json()
    clinic2 = VetClinicInfo(**response.json())

    response = await client.get(f"/admin/vet-clinic/{clinic1.id}", headers={"authorization": admin_token})
    assert response.status_code == 200, response.json()
    resp = VetClinicInfo(**response.json())
    assert resp == clinic1

    response = await client.get(f"/admin/vet-clinic/{clinic1.id}", headers={"authorization": vet_admin_token})
    assert response.status_code == 404, response.json()

    response = await client.get(f"/admin/vet-clinic/{clinic2.id}", headers={"authorization": vet_admin_token})
    assert response.status_code == 200, response.json()
    resp = VetClinicInfo(**response.json())
    assert resp == clinic2

    response = await client.get(f"/admin/vet-clinic/{clinic2.id + 100}", headers={"authorization": vet_admin_token})
    assert response.status_code == 404, response.json()


@pytest.mark.asyncio
async def test_update_vet_clinic(client: AsyncClient):
    admin_token = await create_token(UserRole.GLOBAL_ADMIN)
    vet1_admin_token = await create_token(UserRole.VET_ADMIN)
    vet1_session = await Session.from_jwt(vet1_admin_token)
    vet2_admin_token = await create_token(UserRole.VET_ADMIN)
    vet2_session = await Session.from_jwt(vet2_admin_token)

    response = await client.post("/admin/vet-clinic", headers={"authorization": admin_token}, json={
        "name": "test1",
        "latitude": LON,
        "longitude": LAT,
        "admin_id": None,
    })
    assert response.status_code == 200, response.json()
    clinic = VetClinicInfo(**response.json())

    response = await client.get(f"/admin/vet-clinic/{clinic.id}", headers={"authorization": vet1_admin_token})
    assert response.status_code == 404, response.json()

    response = await client.get(f"/admin/vet-clinic/{clinic.id}", headers={"authorization": vet1_admin_token})
    assert response.status_code == 404, response.json()

    # Admin is vet1

    response = await client.patch(f"/admin/vet-clinic/{clinic.id}", headers={"authorization": admin_token}, json={
        "name": "test123",
        "latitude": LAT,
        "longitude": LON,
        "admin_id": vet1_session.user.id,
    })
    assert response.status_code == 200, response.json()
    resp = VetClinicInfo(**response.json())
    assert resp.name == "test123"
    assert resp.location.latitude == LAT
    assert resp.location.longitude == LON
    assert resp.admin is not None
    assert resp.admin.id == vet1_session.user.id

    response = await client.get(f"/admin/vet-clinic/{clinic.id}", headers={"authorization": vet1_admin_token})
    assert response.status_code == 200, response.json()

    response = await client.get(f"/admin/vet-clinic/{clinic.id}", headers={"authorization": vet2_admin_token})
    assert response.status_code == 404, response.json()

    # Admin is vet2

    response = await client.patch(f"/admin/vet-clinic/{clinic.id}", headers={"authorization": admin_token}, json={
        "admin_id": vet2_session.user.id,
    })
    assert response.status_code == 200, response.json()
    resp = VetClinicInfo(**response.json())
    assert resp.admin.id == vet2_session.user.id

    response = await client.get(f"/admin/vet-clinic/{clinic.id}", headers={"authorization": vet1_admin_token})
    assert response.status_code == 404, response.json()

    response = await client.get(f"/admin/vet-clinic/{clinic.id}", headers={"authorization": vet2_admin_token})
    assert response.status_code == 200, response.json()

    # No admin

    response = await client.patch(f"/admin/vet-clinic/{clinic.id}", headers={"authorization": admin_token}, json={
        "admin_id": 0,
    })
    assert response.status_code == 200, response.json()
    resp = VetClinicInfo(**response.json())
    assert resp.admin is None

    response = await client.get(f"/admin/vet-clinic/{clinic.id}", headers={"authorization": vet1_admin_token})
    assert response.status_code == 404, response.json()

    response = await client.get(f"/admin/vet-clinic/{clinic.id}", headers={"authorization": vet2_admin_token})
    assert response.status_code == 404, response.json()

@pytest.mark.asyncio
async def test_vet_clinic_employees(client: AsyncClient):
    vet_admin_token = await create_token(UserRole.VET_ADMIN)
    vet_admin_session = await Session.from_jwt(vet_admin_token)

    vet1_token = await create_token(UserRole.VET)
    vet1_session = await Session.from_jwt(vet1_token)
    vet2_token = await create_token(UserRole.VET)
    vet2_session = await Session.from_jwt(vet2_token)

    clinic = await VetClinic.create(
        name="test",
        location=await GeoPoint.create(latitude=LAT, longitude=LON),
        admin=vet_admin_session.user,
    )

    response = await client.get(f"/admin/vet-clinic/{clinic.id}/employees", headers={"authorization": vet_admin_token})
    assert response.status_code == 200, response.json()
    resp = PaginatedUsersResponse(**response.json())
    assert resp.count == 0
    assert len(resp.result) == 0

    response = await client.put(f"/admin/vet-clinic/{clinic.id}/employees", headers={"authorization": vet_admin_token}, json={
        "email": vet1_session.user.email,
    })
    assert response.status_code == 204, response.json()

    response = await client.get(f"/admin/vet-clinic/{clinic.id}/employees", headers={"authorization": vet_admin_token})
    assert response.status_code == 200, response.json()
    resp = PaginatedUsersResponse(**response.json())
    assert resp.count == 1
    assert len(resp.result) == 1

    response = await client.put(f"/admin/vet-clinic/{clinic.id}/employees", headers={"authorization": vet_admin_token}, json={
        "email": vet2_session.user.email,
    })
    assert response.status_code == 204, response.json()

    response = await client.get(f"/admin/vet-clinic/{clinic.id}/employees", headers={"authorization": vet_admin_token})
    assert response.status_code == 200, response.json()
    resp = PaginatedUsersResponse(**response.json())
    assert resp.count == 2
    assert len(resp.result) == 2

    response = await client.delete(f"/admin/vet-clinic/{clinic.id}/employees/{vet1_session.user.id}", headers={"authorization": vet_admin_token})
    assert response.status_code == 204, response.json()

    response = await client.get(f"/admin/vet-clinic/{clinic.id}/employees", headers={"authorization": vet_admin_token})
    assert response.status_code == 200, response.json()
    resp = PaginatedUsersResponse(**response.json())
    assert resp.count == 1
    assert len(resp.result) == 1
