"""
Inyección de dependencias globales del API.
- get_db()            → sesión de BD por request
- get_current_user()  → usuario autenticado (JWT)
- require_roles()     → guard de roles RBAC
"""
from typing import Annotated, List

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import decode_token
from app.crud.user import crud_user
from app.db.session import get_db
from app.models.user import User

security = HTTPBearer()

# ── Tipos tipados ──────────────────────────────────────────────
DBSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: DBSession,
) -> User:
    """Valida el Bearer JWT y retorna el usuario autenticado."""
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise UnauthorizedException("Token inválido o expirado.")

    user = await crud_user.get(db, int(payload["sub"]))
    if not user:
        raise UnauthorizedException("Usuario no encontrado.")
    if not user.is_active:
        raise UnauthorizedException("Cuenta desactivada.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: str):
    """
    Guard de roles RBAC.

    Uso:
        @router.get("/admin")
        async def admin_route(user = Depends(require_roles("admin"))):
            ...
    """
    async def role_guard(current_user: CurrentUser) -> User:
        user_roles = {r.name for r in current_user.roles}
        if not user_roles.intersection(set(roles)):
            raise ForbiddenException(
                f"Se requiere uno de los roles: {', '.join(roles)}"
            )
        return current_user
    return role_guard


AdminOnly = Annotated[User, Depends(require_roles("admin"))]
WorkshopOwnerOrAdmin = Annotated[User, Depends(require_roles("admin", "workshop_owner"))]
MechanicOrAdmin = Annotated[User, Depends(require_roles("admin", "mechanic"))]
AnyStaff = Annotated[User, Depends(require_roles("admin", "workshop_owner", "mechanic"))]
