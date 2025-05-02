from typing import Annotated

from fastapi import Header, Depends

from kkp.models import Session, User, UserRole, Animal
from kkp.utils.custom_exception import CustomMessageException


async def jwt_auth_session(
        authorization: str | None = Header(default=None),
        x_token: str | None = Header(default=None),
) -> Session:
    authorization = authorization or x_token
    if not authorization or (session := await Session.from_jwt(authorization)) is None:
        raise CustomMessageException("Invalid session.", 401)

    return session


JwtSessionDep = Annotated[Session, Depends(jwt_auth_session)]


class JWTAuthUser:
    def __init__(self, min_role: UserRole):
        self._min_role = min_role

    async def __call__(self, session: JwtSessionDep) -> User:
        if session.user.role < self._min_role:
            raise CustomMessageException("Insufficient privileges.", 403)

        return session.user


JwtAuthUserDepN = Depends(JWTAuthUser(UserRole.REGULAR))
JwtAuthUserDep = Annotated[User, JwtAuthUserDepN]

JwtAuthVetDepN = Depends(JWTAuthUser(UserRole.VET))
JwtAuthVetDep = Annotated[User, JwtAuthVetDepN]

JwtAuthVetAdminDepN = Depends(JWTAuthUser(UserRole.VET_ADMIN))
JwtAuthVetAdminDep = Annotated[User, JwtAuthVetAdminDepN]

JwtAuthAdminDepN = Depends(JWTAuthUser(UserRole.GLOBAL_ADMIN))
JwtAuthAdminDep = Annotated[User, JwtAuthAdminDepN]


async def animal_dep(animal_id: int) -> Animal:
    if (animal := await Animal.get_or_none(id=animal_id)) is None:
        raise CustomMessageException("Unknown animal.", 404)

    return animal


AnimalDep = Annotated[Animal, Depends(animal_dep)]
