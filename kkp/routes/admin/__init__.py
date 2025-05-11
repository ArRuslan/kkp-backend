from fastapi import APIRouter

from kkp.routes.admin import users

router = APIRouter(prefix="/admin")
router.include_router(users.router)
