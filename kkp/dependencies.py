from typing import Annotated

from fastapi import Header, Depends

from kkp.models import Session, User, UserRole, Animal, AnimalReport, TreatmentReport, VetClinic, VolunteerRequest
from kkp.utils.custom_exception import CustomMessageException


async def jwt_auth_session(
        authorization: str | None = Header(default=None),
        x_token: str | None = Header(default=None),
) -> Session:
    authorization = authorization or x_token
    if not authorization or (session := await Session.from_jwt(authorization)) is None:
        raise CustomMessageException("Invalid session.", 401)
    if not session.active:
        raise CustomMessageException("Session is not active.", 403)

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


async def admin_user_dep(user_id: int, _: JwtAuthAdminDep) -> User:
    if (user := await User.get_or_none(id=user_id)) is None:
        raise CustomMessageException("Unknown user.", 404)

    return user


AdminUserDep = Annotated[User, Depends(admin_user_dep)]


async def admin_animal_dep(_: JwtAuthAdminDep, animal: AnimalDep) -> Animal:
    return animal


AdminAnimalDep = Annotated[Animal, Depends(admin_animal_dep)]


async def animal_report_dep(report_id: int) -> AnimalReport:
    if (report := await AnimalReport.get_or_none(id=report_id).select_related("assigned_to")) is None:
        raise CustomMessageException("Unknown report.", 404)

    return report


AnimalReportDep = Annotated[AnimalReport, Depends(animal_report_dep)]


async def treatment_report_dep(treatment_report_id: int) -> TreatmentReport:
    if (report := await TreatmentReport.get_or_none(id=treatment_report_id).select_related("report")) is None:
        raise CustomMessageException("Unknown treatment report.", 404)

    return report


TreatmentReportDep = Annotated[TreatmentReport, Depends(treatment_report_dep)]


async def admin_vet_clinic_dep(vet_clinic_id: int, _: JwtAuthVetAdminDep) -> VetClinic:
    if (clinic := await VetClinic.get_or_none(id=vet_clinic_id).select_related("admin")) is None:
        raise CustomMessageException("Unknown vet clinic.", 404)

    return clinic


AdminVetClinicDep = Annotated[VetClinic, Depends(admin_vet_clinic_dep)]


async def admin_vol_request_dep(volunteer_request_id: int, _: JwtAuthAdminDep) -> VolunteerRequest:
    if (vol_request := await VolunteerRequest.get_or_none(id=volunteer_request_id).select_related("user")) is None:
        raise CustomMessageException("Unknown volunteer request.", 404)

    return vol_request

AdminVolunteerRequestDep = Annotated[VolunteerRequest, Depends(admin_vol_request_dep)]


async def admin_treatment_dep(_: JwtAuthAdminDep, report: TreatmentReportDep) -> TreatmentReport:
    return report


AdminTreatmentReportDep = Annotated[TreatmentReport, Depends(admin_treatment_dep)]
