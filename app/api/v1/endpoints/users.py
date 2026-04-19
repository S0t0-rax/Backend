"""
Endpoints de Gestión de Usuarios (Admin) — /api/v1/users
"""
from typing import List
from fastapi import APIRouter, HTTPException

from app.api.dependencies import AdminOnly, DBSession
from app.crud.user import crud_user
from app.schemas.user import UserResponse, AdminUserUpdate
from sqlalchemy import select
from app.models.user import User
from app.models.role import Role

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
