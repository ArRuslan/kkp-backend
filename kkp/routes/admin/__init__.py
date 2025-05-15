from fastapi import APIRouter

from kkp.routes.admin import users, animals, vet_clinics, volunteer_requests

router = APIRouter(prefix="/admin")
router.include_router(users.router)
router.include_router(animals.router)
router.include_router(vet_clinics.router)
router.include_router(volunteer_requests.router)
