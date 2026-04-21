"""
CRUD de Workshop con búsqueda geoespacial (talleres cercanos).
"""
from typing import Any, List

from geoalchemy2.functions import ST_GeogFromText, ST_DWithin, ST_Distance
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.workshop import Workshop
from app.schemas.workshop import WorkshopCreate, WorkshopUpdate


class CRUDWorkshop(CRUDBase[Workshop, WorkshopCreate, WorkshopUpdate]):

    async def create(
        self, db: AsyncSession, *, obj_in: WorkshopCreate, owner_id: int
    ) -> Workshop:
        point_wkt = f"SRID=4326;POINT({obj_in.longitude} {obj_in.latitude})"
        workshop = Workshop(
            owner_id=owner_id,
            name=obj_in.name,
            tax_id=obj_in.tax_id,
            address_text=obj_in.address_text,
            geom=ST_GeogFromText(point_wkt),
        )
        db.add(workshop)
        await db.flush()
        await db.refresh(workshop)
        return workshop

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: Workshop,
        obj_in: WorkshopUpdate | dict[str, Any],
    ) -> Workshop:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        if "latitude" in update_data or "longitude" in update_data:
            lat = update_data.get("latitude", db_obj.latitude)
            lng = update_data.get("longitude", db_obj.longitude)
            point_wkt = f"SRID=4326;POINT({lng} {lat})"
            db_obj.geom = ST_GeogFromText(point_wkt)

        return await super().update(db, db_obj=db_obj, obj_in=update_data)

    async def find_nearby(

        self,
        db: AsyncSession,
        latitude: float,
        longitude: float,
        radius_meters: float = 10000,
        limit: int = 20,
    ) -> List[tuple[Workshop, float]]:
        """
        Retorna talleres dentro del radio, ordenados por distancia.
        Usa el índice GIST: idx_workshops_geom para máxima performance.
        """
        point = f"SRID=4326;POINT({longitude} {latitude})"
        geog_point = ST_GeogFromText(point)

        result = await db.execute(
            select(
                Workshop,
                ST_Distance(Workshop.geom, geog_point).label("distance_meters"),
            )
            .where(ST_DWithin(Workshop.geom, geog_point, radius_meters))
            .order_by("distance_meters")
            .limit(limit)
        )
        return [(row.Workshop, row.distance_meters) for row in result.all()]


crud_workshop = CRUDWorkshop(Workshop)
