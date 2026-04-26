"""
Endpoints de Autenticación — /api/v1/auth
"""
from fastapi import APIRouter

from app.api.dependencies import CurrentUser, DBSession
from app.core.exceptions import UnauthorizedException
from app.core.exceptions import ConflictException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
    hash_password,
)
from app.crud.user import crud_user
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse, ChangePasswordRequest
from app.schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/auth", tags=["🔐 Autenticación"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(data: UserCreate, db: DBSession):
    """Registra un nuevo usuario. Rol por defecto: client."""
    # Solo permitir creación pública de Dueños de Taller desde la web.
    # Los mecánicos deben ser creados por un dueño y los clientes solo desde la app móvil.
    role = (data.role_name or "client").lower()
    if role not in ["workshop_owner", "client"]:
        raise ConflictException(
            f"El rol '{role}' no es válido para registro público. "
            "Solo dueños de taller y clientes pueden registrarse directamente."
        )

    existing = await crud_user.get_by_email(db, data.email)
    if existing:
        raise ConflictException(f"El email '{data.email}' ya está registrado.")

    user = await crud_user.create(db, obj_in=data)
    return UserResponse.from_orm_with_roles(user)


@router.post("/login", response_model=TokenResponse)
async def login(credentials: LoginRequest, db: DBSession):
    """Autentica al usuario y retorna Access + Refresh tokens JWT."""
    user = await crud_user.get_by_email(db, credentials.email)
    if not user or not verify_password(credentials.password, user.password_hash):
        raise UnauthorizedException("Credenciales incorrectas.")
    if not user.is_active:
        raise UnauthorizedException("Cuenta desactivada.")

    roles = [r.name for r in user.roles]
    return TokenResponse(
        access_token=create_access_token(str(user.id), roles),
        refresh_token=create_refresh_token(str(user.id), roles),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: DBSession):
    """Genera nuevos tokens desde un refresh token válido."""
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise UnauthorizedException("Refresh token inválido o expirado.")

    user = await crud_user.get(db, int(payload["sub"]))
    if not user or not user.is_active:
        raise UnauthorizedException("Usuario no encontrado.")

    roles = [r.name for r in user.roles]
    return TokenResponse(
        access_token=create_access_token(str(user.id), roles),
        refresh_token=create_refresh_token(str(user.id), roles),
    )


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUser):
    """Perfil del usuario autenticado."""
    return UserResponse.from_orm_with_roles(current_user)


@router.put('/change-password', status_code=200)
async def change_password(data: ChangePasswordRequest, db: DBSession, current_user: CurrentUser):
    if not verify_password(data.current_password, current_user.password_hash):
        raise UnauthorizedException('La contraseña actual es incorrecta.')
    current_user.password_hash = hash_password(data.new_password)
    db.add(current_user)
    await db.flush()
    return {'message': 'Contraseña actualizada correctamente.'}


@router.put("/me", response_model=UserResponse)
async def update_me(data: UserUpdate, db: DBSession, current_user: CurrentUser):
    """Actualiza el perfil del usuario autenticado."""
    if data.full_name is not None:
        current_user.full_name = data.full_name
    if data.phone is not None:
        current_user.phone = data.phone
    if data.email is not None and data.email != current_user.email:
        # Verificar si el nuevo email ya está en uso
        existing = await crud_user.get_by_email(db, data.email)
        if existing:
            from app.core.exceptions import ConflictException
            raise ConflictException(f"El email '{data.email}' ya está en uso.")
        current_user.email = data.email
    
    db.add(current_user)
    await db.flush()
    await db.refresh(current_user)
    return UserResponse.from_orm_with_roles(current_user)

