from fastapi import APIRouter, Query

from kkp.dependencies import JwtAuthAdminDepN, AdminVetClinicDep, JwtAuthVetAdminDep
from kkp.models import VetClinic, GeoPoint, User, UserRole
from kkp.schemas.admin.vet_clinics import CreateVetClinicRequest, EditVetClinicRequest, EditEmployeeRequest, \
    VetClinicsQuery
from kkp.schemas.common import PaginationResponse, PaginationQuery
from kkp.schemas.users import UserInfo
from kkp.schemas.vet_clinics import VetClinicInfo
from kkp.utils.custom_exception import CustomMessageException

router = APIRouter(prefix="/vet-clinic")


@router.get("", response_model=PaginationResponse[VetClinicInfo])
async def get_clinics(user: JwtAuthVetAdminDep, query: VetClinicsQuery = Query()):
    db_query = VetClinic.filter(admin=user) if user.role < UserRole.GLOBAL_ADMIN else VetClinic.all()

    if query.id is not None:
        db_query = db_query.filter(id=query.id)
    if query.admin_id is not None:
        db_query = db_query.filter(admin__id=query.admin_id)

    order = query.order_by
    if query.order == "desc":
        order = f"-{order}"

    db_query = db_query.order_by(order)

    return {
        "count": await db_query.count(),
        "result": [
            await clinic.to_json()
            for clinic in await db_query \
                .limit(query.page_size) \
                .offset(query.page_size * (query.page - 1))
        ],
    }


@router.get("/{vet_clinic_id}", response_model=VetClinicInfo)
async def get_vet_clinic(user: JwtAuthVetAdminDep, clinic: AdminVetClinicDep):
    if user.role < UserRole.GLOBAL_ADMIN and clinic.admin != user:
        raise CustomMessageException("Unknown vet clinic.", 404)

    return await clinic.to_json()


@router.post("", response_model=VetClinicInfo, dependencies=[JwtAuthAdminDepN])
async def create_vet_clinic(data: CreateVetClinicRequest):
    location = await GeoPoint.create(name=data.name, latitude=data.latitude, longitude=data.longitude)

    admin = None
    if data.admin_id is not None:
        if (admin := await User.get_or_none(id=data.admin_id)) is None:
            raise CustomMessageException("Unknown user.", 404)

    clinic = await VetClinic.create(
        name=data.name,
        location=location,
        admin=admin,
    )

    return await clinic.to_json()


@router.patch("/{vet_clinic_id}", response_model=VetClinicInfo)
async def edit_vet_clinic(user: JwtAuthVetAdminDep, clinic: AdminVetClinicDep, data: EditVetClinicRequest):
    if user.role < UserRole.GLOBAL_ADMIN and clinic.admin != user:
        raise CustomMessageException("Unknown vet clinic.", 404)

    to_update = []
    if data.name is not None:
        clinic.name = data.name
        to_update.append("name")
    if user.role == UserRole.GLOBAL_ADMIN and data.admin_id is not None:
        if data.admin_id > 0:
            if clinic.admin is not None:
                clinic.admin = None
                to_update.append("admin_id")
        else:
            if (new_admin := await User.get_or_none(id=data.admin_id)) is None:
                raise CustomMessageException("Unknown user.", 404)
            clinic.admin = new_admin
            to_update.append("admin_id")
    if data.latitude is not None and data.longitude is not None:
        clinic.location.name = None
        await clinic.location.save(update_fields=["name"])
        clinic.location = await GeoPoint.create(name=clinic.name, latitude=data.latitude, longitude=data.longitude)
        to_update.append("location_id")

    if to_update:
        await clinic.save(update_fields=to_update)

    return await clinic.to_json()


@router.delete("/{vet_clinic_id}", dependencies=[JwtAuthAdminDepN], status_code=204)
async def delete_vet_clinic(clinic: AdminVetClinicDep):
    clinic.location.name = None
    await clinic.location.save(update_fields=["name"])
    await clinic.delete()


@router.get("/{vet_clinic_id}/employees", response_model=PaginationResponse[UserInfo])
async def get_clinic_employees(user: JwtAuthVetAdminDep, clinic: AdminVetClinicDep, query: PaginationQuery = Query()):
    if user.role < UserRole.GLOBAL_ADMIN and clinic.admin != user:
        raise CustomMessageException("Unknown vet clinic.", 404)

    return {
        "count": await clinic.employees.all().count(),
        "result": [
            await clinic.to_json()
            for clinic in await clinic.employees.all() \
                .limit(query.page_size) \
                .offset(query.page_size * (query.page - 1))
        ],
    }


@router.put("/{vet_clinic_id}/employees", status_code=204)
async def add_clinic_employee(user: JwtAuthVetAdminDep, clinic: AdminVetClinicDep, data: EditEmployeeRequest):
    if user.role < UserRole.GLOBAL_ADMIN and clinic.admin != user:
        raise CustomMessageException("Unknown vet clinic.", 404)

    if (emp_user := await User.get_or_none(email=data.email)) is None:
        raise CustomMessageException("Unknown user.", 404)

    await clinic.employees.add(emp_user)


@router.delete("/{vet_clinic_id}/employees", status_code=204)
async def remove_clinic_employee(user: JwtAuthVetAdminDep, clinic: AdminVetClinicDep, data: EditEmployeeRequest):
    if user.role < UserRole.GLOBAL_ADMIN and clinic.admin != user:
        raise CustomMessageException("Unknown vet clinic.", 404)

    if (emp_user := await User.get_or_none(email=data.email)) is None:
        raise CustomMessageException("Unknown user.", 404)

    await clinic.employees.remove(emp_user)
