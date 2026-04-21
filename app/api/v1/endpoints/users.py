"""
Endpoints de Gestión de Usuarios (Admin) — /api/v1/users
"""
from typing import List
from fastapi import APIRouter, HTTPException

from app.api.dependencies import AdminOnly, DBSession, WorkshopOwnerOrAdmin
from app.crud.user import crud_user
from app.crud.workshop import crud_workshop
from app.schemas.user import UserResponse, AdminUserUpdate, UserCreate
from sqlalchemy import select
from app.models.user import User
from app.models.role import Role
from app.models.workshop import Workshop
from app.core.exceptions import ConflictException
from app.models.workshop import workshop_staff_table
from sqlalchemy import distinct, select, and_, outerjoin
from app.models.service_order import ServiceOrder
from app.schemas.user import MechanicStaffResponse

router = APIRouter(prefix="/users", tags=["👥 Gestión de Usuarios"])


@router.get("", response_model=List[UserResponse])
async def list_users(
    db: DBSession,
    admin_user: AdminOnly,
    skip: int = 0,
    limit: int = 100,
):
    """Retorna listado completo de usuarios (Solo Admin)."""
    result = await db.execute(select(User).offset(skip).limit(limit))
    users = result.scalars().all()
    return [UserResponse.from_orm_with_roles(u) for u in users]


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    data: AdminUserUpdate,
    db: DBSession,
    admin_user: AdminOnly,
):
    """
    Edita un usuario (Solo Admin).
    Permite modificar roles, activar/desactivar, y detalles de perfil.
    """
    user = await crud_user.get(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    # 1. Update basic fields
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.phone is not None:
        user.phone = data.phone
    if data.is_active is not None:
        user.is_active = data.is_active

    # 2. Update role if provided
    if data.role_name:
        role_result = await db.execute(select(Role).where(Role.name == data.role_name))
        role = role_result.scalar_one_or_none()
        if not role:
            raise HTTPException(status_code=400, detail=f"Rol '{data.role_name}' inválido.")
        user.roles = [role]

    db.add(user)
    await db.flush()
    await db.refresh(user)
    
    return UserResponse.from_orm_with_roles(user)


@router.get("/my-staff", response_model=list[MechanicStaffResponse])
async def my_staff(db: DBSession, owner: WorkshopOwnerOrAdmin):
    """Retorna la lista de mecánicos asignados a los talleres del dueño autenticado.

    Para cada mecánico devuelve si está ocupado (orden en progreso) y el taller donde
    está trabajando actualmente (si aplica).
    """
    # Subconsulta: órdenes activas (started_at IS NOT NULL AND finished_at IS NULL)
    active_so = (
        select(ServiceOrder.mechanic_id, ServiceOrder.workshop_id)
        .where(ServiceOrder.started_at.isnot(None))
        .where(ServiceOrder.finished_at.is_(None))
        .subquery()
    )

    q = (
        select(User, active_so.c.workshop_id)
        .distinct()
        .join(workshop_staff_table, workshop_staff_table.c.mechanic_id == User.id)
        .join(Workshop, workshop_staff_table.c.workshop_id == Workshop.id)
        .outerjoin(active_so, active_so.c.mechanic_id == User.id)
        .where(Workshop.owner_id == owner.id)
    )

    rows = await db.execute(q)
    results = []
    for row in rows.all():
        user = row.User
        active_workshop_id = row[1]
        workshop_name = None
        if active_workshop_id:
            w = await crud_workshop.get(db, active_workshop_id)
            workshop_name = w.name if w else None

        is_busy = bool(active_workshop_id)

        results.append(
            MechanicStaffResponse(
                **UserResponse.from_orm_with_roles(user).model_dump(),
                is_busy=is_busy,
                workshop_id=active_workshop_id,
                workshop_name=workshop_name,
            )
        )

    return results


@router.post("/mechanics", response_model=UserResponse, status_code=201)
async def create_mechanic(
    data: UserCreate,
    db: DBSession,
    owner: WorkshopOwnerOrAdmin,
    workshop_id: int | None = None,
):
    """Permite a un dueño de taller crear una cuenta de mecánico y asignarlo a un taller.

    - `data.password` es la contraseña inicial que asigna el dueño.
    - `workshop_id` (opcional) indica en qué taller trabajará el mecánico.
    """
    # 1. Validaciones básicas
    existing = await crud_user.get_by_email(db, data.email)
    if existing:
        raise ConflictException(f"El email '{data.email}' ya está registrado.")

    # Forzamos el rol a 'mechanic' independientemente de lo que envíe el cliente
    data.role_name = "mechanic"

    # 2. Crear usuario mecánico
    user = await crud_user.create(db, obj_in=data)

    # 3. Si se indicó workshop_id, verificar pertenencia y asignar
    if workshop_id is not None:
        workshop = await crud_workshop.get(db, workshop_id)
        if not workshop:
            raise HTTPException(status_code=404, detail="Taller no encontrado.")
        # Si el owner no es admin, debe ser propietario del taller
        owner_roles = {r.name for r in owner.roles}
        if "admin" not in owner_roles and workshop.owner_id != owner.id:
            raise HTTPException(status_code=403, detail="No puedes asignar mecánicos a un taller que no administras.")

        workshop.mechanics.append(user)
        db.add(workshop)
        await db.flush()

    await db.refresh(user)
    return UserResponse.from_orm_with_roles(user)


@router.delete("/{user_id}")
async def delete_user_logical(
    user_id: int,
    db: DBSession,
    admin_user: AdminOnly,
):
    """
    Borrado lógico de usuario (suspensión).
    """
    user = await crud_user.get(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    
    if user.id == admin_user.id:
        raise HTTPException(status_code=400, detail="No puedes eliminarte a ti mismo.")

    user.is_active = False
    db.add(user)
    await db.flush()
    
    return {"message": "Usuario desactivado correctamente."}
