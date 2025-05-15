from fastapi import APIRouter, Query

from kkp.db.point import STDistanceSphere, Point
from kkp.dependencies import JwtAuthVetAdminDep
from kkp.models import VetClinic
from kkp.schemas.common import PaginationResponse
from kkp.schemas.vet_clinics import VetClinicInfo, NearVetClinicsQuery

router = APIRouter(prefix="/vet-clinic")


@router.get("/near", response_model=PaginationResponse[VetClinicInfo])
async def get_near_clinics(user: JwtAuthVetAdminDep, query: NearVetClinicsQuery = Query()):
    radius = min(max(query.radius, 100), 15000)
    db_query = VetClinic.annotate(dist=STDistanceSphere("location__point", Point(query.lon, query.lat))) \
        .filter(dist__lt=radius) \
        .select_related("location", "admin") \
        .order_by("dist")

    return {
        "count": await db_query.count(),
        "result": [
            await clinic.to_json()
            for clinic in await db_query.limit(query.page_size).offset(query.page_size * (query.page - 1))
        ],
    }
