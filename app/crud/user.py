"""
CRUD de Usuario con soporte de localización GPS.
"""
from typing import Optional

from geoalchemy2.functions import ST_GeogFromText
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.crud.base import CRUDBase
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):

    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, *, obj_in: UserCreate) -> User:
        from app.models.role import Role
        role_name = obj_in.role_name or "client"
        role_result = await db.execute(select(Role).where(Role.name == role_name))
        role = role_result.scalar_one_or_none()
        
        # Si no existe el rol predeterminado en BDD (por ser nueva db), lo creamos
        if not role:
            role = Role(name=role_name, description=f"Role: {role_name}")
            db.add(role)
            await db.flush()

        user = User(
            email=obj_in.email,
            password_hash=hash_password(obj_in.password),
            full_name=obj_in.full_name,
            phone=obj_in.phone,
            roles=[role]
        )
        db.add(user)
        
        await db.flush()
        await db.refresh(user)
        return user

    async def update_location(
        self, db: AsyncSession, *, user: User, latitude: float, longitude: float
    ) -> User:
        """
        Actualiza la ubicación GPS del usuario usando PostGIS.
        Formato WKT: POINT(longitude latitude)  ← PostGIS usa lon, lat
        """
        user.current_location = ST_GeogFromText(f"SRID=4326;POINT({longitude} {latitude})")
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return user


crud_user = CRUDUser(User)
