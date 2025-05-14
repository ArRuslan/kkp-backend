import pytest
from httpx import AsyncClient

from kkp.models import UserRole, MediaType
from kkp.schemas.animal_reports import AnimalReportInfo
from kkp.schemas.common import PaginationResponse
from kkp.schemas.media import CreateMediaUploadResponse, MediaInfo
from tests.conftest import create_token

IMG_1x1_PIXEL_RED = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010802000000907753"
    "de000000017352474200aece1ce90000000c49444154185763f8cfc000000301"
    "0100632455d30000000049454e44ae426082"
)


@pytest.mark.asyncio
async def test_upload_photo(client: AsyncClient):
    user_token = await create_token(UserRole.REGULAR)

    response = await client.post("/media", headers={"authorization": user_token}, json={
        "type": MediaType.PHOTO.value,
        "size": len(IMG_1x1_PIXEL_RED),
    })
    assert response.status_code == 200, response.json()
    resp = CreateMediaUploadResponse(**response.json())

    async with AsyncClient() as cl:
        upload_response = await cl.put(resp.upload_url, content=IMG_1x1_PIXEL_RED)
        assert upload_response.status_code == 200

    response = await client.post(f"/media/{resp.id}/finalize", headers={"authorization": user_token})
    assert response.status_code == 200, response.json()
    resp = MediaInfo(**response.json())

    async with AsyncClient() as cl:
        media_response = await cl.get(resp.url)
        assert media_response.status_code == 200
        assert await media_response.aread() == IMG_1x1_PIXEL_RED
