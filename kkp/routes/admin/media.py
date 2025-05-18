from fastapi import APIRouter, Query
from s3lite import S3Exception

from kkp.config import S3, config
from kkp.dependencies import JwtAuthAdminDepN, AdminMediaDep
from kkp.models import Media
from kkp.schemas.admin.media import MediaQuery
from kkp.schemas.common import PaginationResponse
from kkp.schemas.media import MediaInfo

router = APIRouter(prefix="/media", dependencies=[JwtAuthAdminDepN])


@router.get("", response_model=PaginationResponse[MediaInfo])
async def get_treatment_reports(query: MediaQuery = Query()):
    media_query = Media.filter()

    if query.id is not None:
        media_query = media_query.filter(id=query.id)
    if query.type is not None:
        media_query = media_query.filter(type=query.type)
    if query.status is not None:
        media_query = media_query.filter(status=query.status)
    if query.uploaded_by_id is not None:
        media_query = media_query.filter(uploaded_by__id=query.uploaded_by_id)

    order = query.order_by
    if query.order == "desc":
        order = f"-{order}"

    media_query = media_query.order_by(order)

    return {
        "count": await media_query.count(),
        "result": [
            media.to_json()
            for media in await media_query \
                .limit(query.page_size) \
                .offset(query.page_size * (query.page - 1))
        ],
    }


@router.get("/{media_id}", response_model=MediaInfo)
async def get_media(media: AdminMediaDep):
    return await media.to_json()


@router.delete("/{media_id}", status_code=204)
async def delete_media(media: AdminMediaDep):
    try:
        await S3.delete_object(config.s3_bucket_name, media.object_key())
    except S3Exception:
        ...
    await media.delete()