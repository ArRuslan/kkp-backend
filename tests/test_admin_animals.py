import pytest
from httpx import AsyncClient

from kkp.models import UserRole, Animal, AnimalStatus, AnimalGender, Media, MediaType, \
    MediaStatus
from kkp.schemas.animals import AnimalInfo
from kkp.schemas.common import PaginationResponse
from tests.conftest import create_token

LON = 42.42424242
LAT = 24.24242424


class PaginatedAnimalResponse(PaginationResponse[AnimalInfo]):
    ...


@pytest.mark.asyncio
async def test_admin_get_animals_empty(client: AsyncClient):
    token = await create_token(UserRole.GLOBAL_ADMIN)
    response = await client.get("/admin/animals", headers={"authorization": token})
    assert response.status_code == 200, response.json()
    resp = PaginatedAnimalResponse(**response.json())
    assert resp.count == 0
    assert len(resp.result) == 0


@pytest.mark.asyncio
async def test_admin_get_animals_pagination_filtering(client: AsyncClient):
    token = await create_token(UserRole.GLOBAL_ADMIN)

    statuses = list(AnimalStatus)
    animals = [
        await Animal.create(name=f"test {i}", breed="test idk", status=statuses[i % len(statuses)])
        for i in range(100)
    ]
    animal_ids = [animals.id for animals in animals]
    animal_statuses_ids = {
        status: [animal.id for animal in animals if animal.status == status]
        for status in statuses
    }

    response = await client.get("/admin/animals?page=1&page_size=25", headers={"authorization": token})
    assert response.status_code == 200, response.json()
    resp = PaginatedAnimalResponse(**response.json())
    assert resp.count == 100
    assert len(resp.result) == 25
    assert [animal.id for animal in resp.result] == animal_ids[0:25]

    response = await client.get("/admin/animals?page=1&page_size=25&order=desc", headers={"authorization": token})
    assert response.status_code == 200, response.json()
    resp = PaginatedAnimalResponse(**response.json())
    assert resp.count == 100
    assert len(resp.result) == 25
    assert [animal.id for animal in resp.result] == animal_ids[:-25 - 1:-1]

    for status in statuses:
        response = await client.get(f"/admin/animals?page=1&page_size=100&order=desc&status={status.value}", headers={"authorization": token})
        assert response.status_code == 200, response.json()
        resp = PaginatedAnimalResponse(**response.json())
        assert resp.count == len(animal_statuses_ids[status])
        assert len(resp.result) == len(animal_statuses_ids[status])
        assert [animal.id for animal in resp.result] == animal_statuses_ids[status][::-1]


@pytest.mark.asyncio
async def test_admin_get_animal(client: AsyncClient):
    animal = await Animal.create(name=f"test 123", breed="test idk", status=AnimalStatus.FOUND)

    token = await create_token(UserRole.GLOBAL_ADMIN)
    response = await client.get(f"/admin/animals/{animal.id}", headers={"authorization": token})
    assert response.status_code == 200, response.json()
    resp = AnimalInfo(**response.json())
    assert resp.name == "test 123"
    assert resp.status is AnimalStatus.FOUND


@pytest.mark.asyncio
async def test_admin_edit_animal(client: AsyncClient):
    animal = await Animal.create(name=f"test 123", breed="test idk", status=AnimalStatus.FOUND)

    media1 = await Media.create(type=MediaType.PHOTO, status=MediaStatus.UPLOADED)
    media2 = await Media.create(type=MediaType.PHOTO, status=MediaStatus.UPLOADED)
    media3 = await Media.create(type=MediaType.PHOTO, status=MediaStatus.UPLOADED)
    media4 = await Media.create(type=MediaType.PHOTO, status=MediaStatus.UPLOADED)

    await animal.medias.add(media1, media2, media3)

    token = await create_token(UserRole.GLOBAL_ADMIN)
    response = await client.get(f"/admin/animals/{animal.id}", headers={"authorization": token})
    assert response.status_code == 200, response.json()
    resp = AnimalInfo(**response.json())
    assert resp.name == "test 123"
    assert resp.current_location is None
    assert resp.breed == "test idk"
    assert resp.status is AnimalStatus.FOUND
    assert resp.description == ""
    assert resp.gender is AnimalGender.UNKNOWN
    assert resp.media.count == 3
    assert set([media.id for media in resp.media.result]) == {media1.id, media2.id, media3.id}

    response = await client.patch(f"/admin/animals/{animal.id}", headers={"authorization": token}, json={
        "name": "updated 456",
        "breed": "idk 123",
        "status": AnimalStatus.WAITING_FOR_ADOPTION,
        "description": "some description",
        "add_media_ids": [media3.id, media4.id],
        "remove_media_ids": [media1.id, media2.id],
        "current_latitude": LAT,
        "current_longitude": LON,
        "gender": AnimalGender.FEMALE,
    })
    assert response.status_code == 200, response.json()
    resp = AnimalInfo(**response.json())
    assert resp.name == "updated 456"
    assert resp.breed == "idk 123"
    assert resp.status is AnimalStatus.WAITING_FOR_ADOPTION
    assert resp.description == "some description"
    assert resp.current_location is not None
    assert resp.current_location.latitude == LAT
    assert resp.current_location.longitude == LON
    assert resp.gender is AnimalGender.FEMALE
    assert resp.media.count == 2
    assert set([media.id for media in resp.media.result]) == {media3.id, media4.id}


@pytest.mark.asyncio
async def test_admin_delete_animal(client: AsyncClient):
    animal = await Animal.create(name=f"test 123", breed="test idk", status=AnimalStatus.FOUND)

    token = await create_token(UserRole.GLOBAL_ADMIN)
    response = await client.get(f"/admin/animals/{animal.id}", headers={"authorization": token})
    assert response.status_code == 200, response.json()
    assert AnimalInfo(**response.json())

    response = await client.delete(f"/admin/animals/{animal.id}", headers={"authorization": token})
    assert response.status_code == 204, response.json()

    response = await client.get(f"/admin/animals/{animal.id}", headers={"authorization": token})
    assert response.status_code == 404, response.json()
