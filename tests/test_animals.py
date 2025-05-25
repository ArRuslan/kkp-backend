import pytest
from httpx import AsyncClient

from kkp.models import UserRole, Animal, AnimalStatus, Media, MediaType, MediaStatus
from kkp.schemas.animals import AnimalInfo
from kkp.schemas.common import PaginationResponse
from tests.conftest import create_token, check_sorted

STATUSES = [
    AnimalStatus.FOUND,
    AnimalStatus.ON_TREATMENT,
    AnimalStatus.RELEASED,
    AnimalStatus.WAITING_FOR_ADOPTION,
    AnimalStatus.ADOPTED,
]


class PaginationAnimalResponse(PaginationResponse[AnimalInfo]):
    pass


@pytest.mark.asyncio
async def test_get_animals(client: AsyncClient):
    await Animal.bulk_create([
        Animal(
            name=f"test{idx}",
            breed="idk",
            status=STATUSES[idx % len(STATUSES)],
            description=f"test animal\n{idx}",
        ) for idx in range(50)
    ])

    response = await client.get("/animals?page=1&page_size=25")
    assert response.status_code == 200, response.json()
    resp = PaginationAnimalResponse(**response.json())
    assert resp.count == 50
    assert len(resp.result) == 25
    assert check_sorted([animal.id for animal in resp.result])

    response = await client.get("/animals?page=2&page_size=30&order_by=id&order=desc")
    assert response.status_code == 200, response.json()
    resp = PaginationAnimalResponse(**response.json())
    assert resp.count == 50
    assert len(resp.result) == 20
    assert check_sorted([animal.id for animal in resp.result][::-1])


@pytest.mark.asyncio
async def test_get_animal(client: AsyncClient):
    animal = await Animal.create(
        name=f"test123",
        breed="idk",
        status=AnimalStatus.ON_TREATMENT,
        description=f"test animal\nidk",
    )

    response = await client.get(f"/animals/{animal.id}")
    assert response.status_code == 200, response.json()
    resp = AnimalInfo(**response.json())
    assert resp.name == "test123"
    assert resp.breed == "idk"
    assert resp.status == AnimalStatus.ON_TREATMENT
    assert resp.description == "test animal\nidk"


@pytest.mark.asyncio
async def test_edit_animal(client: AsyncClient):
    vet_token = await create_token(UserRole.VET)

    animal = await Animal.create(
        name=f"test123",
        breed="idk",
        status=AnimalStatus.ON_TREATMENT,
        description=f"test animal\nidk",
    )

    media1 = await Media.create(type=MediaType.PHOTO, status=MediaStatus.UPLOADED)
    media2 = await Media.create(type=MediaType.PHOTO, status=MediaStatus.UPLOADED)
    media3 = await Media.create(type=MediaType.PHOTO, status=MediaStatus.UPLOADED)
    media4 = await Media.create(type=MediaType.PHOTO, status=MediaStatus.CREATED)

    await animal.medias.add(media1, media2)

    response = await client.get(f"/animals/{animal.id}")
    assert response.status_code == 200, response.json()
    resp = AnimalInfo(**response.json())
    assert resp.name == "test123"
    assert resp.breed == "idk"
    assert resp.status == AnimalStatus.ON_TREATMENT
    assert resp.description == "test animal\nidk"
    assert resp.media.count == 2
    assert len(resp.media.result) == 2
    assert {media.id for media in resp.media.result} == {media1.id, media2.id}

    response = await client.patch(f"/animals/{animal.id}", headers={"authorization": vet_token}, json={
        "add_media_ids": [media3.id, media4.id],
        "remove_media_ids": [media1.id],
        "name": "test456",
        "description": "123 test animal",
    })
    assert response.status_code == 200, response.json()
    resp = AnimalInfo(**response.json())
    assert resp.name == "test456"
    assert resp.breed == "idk"
    assert resp.status == AnimalStatus.ON_TREATMENT
    assert resp.description == "123 test animal"
    assert resp.media.count == 2
    assert len(resp.media.result) == 2
    assert {media.id for media in resp.media.result} == {media3.id, media2.id}
