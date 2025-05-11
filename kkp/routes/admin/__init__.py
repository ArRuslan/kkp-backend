from fastapi import APIRouter

from kkp.routes.admin import users, animals

router = APIRouter(prefix="/admin")
router.include_router(users.router)
router.include_router(animals.router)
