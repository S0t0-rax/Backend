"""
CRUD para Vehículos (Cars).
"""
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.car import Car
from app.schemas.car import CarCreate, CarUpdate


class CRUDCar(CRUDBase[Car, CarCreate, CarUpdate]):
    
    async def get_by_owner(
        self, db: AsyncSession, owner_id: int, skip: int = 0, limit: int = 50
    ) -> List[Car]:
        """Lista los vehículos de un dueño específico."""
        result = await db.execute(
            select(Car)
            .where(Car.owner_id == owner_id)
            .offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_plate(self, db: AsyncSession, plate: str) -> Optional[Car]:
        """Busca un vehículo por su placa (unique)."""
        result = await db.execute(select(Car).where(Car.license_plate == plate))
        return result.scalar_one_or_none()

    async def create_with_owner(
        self, db: AsyncSession, *, obj_in: CarCreate, owner_id: int
    ) -> Car:
        """Crea un vehículo asignándole un dueño."""
        db_obj = Car(
            **obj_in.model_dump(),
            owner_id=owner_id
        )
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj


crud_car = CRUDCar(Car)
