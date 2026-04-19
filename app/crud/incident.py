"""
CRUD de Incidente con soporte geoespacial.
"""
from typing import List, Optional

from geoalchemy2.functions import ST_GeogFromText, ST_DWithin, ST_Distance
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.incident import Incident, IncidentPhoto
from app.schemas.incident import IncidentCreate, IncidentUpdate


class CRUDIncident(CRUDBase[Incident, IncidentCreate, IncidentUpdate]):

    async def get_with_photos(self, db: AsyncSession, id: int) -> Optional[Incident]:
        result = await db.execute(
            select(Incident)
            .options(selectinload(Incident.photos))
            .where(Incident.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_client(
        self, db: AsyncSession, client_id: int, skip: int = 0, limit: int = 50
    ) -> List[Incident]:
        result = await db.execute(
            select(Incident)
            .where(Incident.client_id == client_id)
            .offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def create(
        self, db: AsyncSession, *, obj_in: IncidentCreate, client_id: int
    ) -> Incident:
        """Crea incidente con ubicación GPS (PostGIS POINT)."""
        point_wkt = f"SRID=4326;POINT({obj_in.longitude} {obj_in.latitude})"
        incident = Incident(
            client_id=client_id,
            car_id=obj_in.car_id,
            incident_location=ST_GeogFromText(point_wkt),
            address_reference=obj_in.address_reference,
            description=obj_in.description,
        )
        db.add(incident)
        await db.flush()
        await db.refresh(incident)
        return incident

    async def find_nearby(
        self,
        db: AsyncSession,
        latitude: float,
        longitude: float,
        radius_meters: float = 5000,
    ) -> List[Incident]:
        """
        Busca incidentes abiertos dentro del radio especificado.
        Usa índice GIST de PostGIS: ST_DWithin para performance.
        """
        point = f"SRID=4326;POINT({longitude} {latitude})"
        result = await db.execute(
            select(Incident)
            .where(
                Incident.status == "open",
                ST_DWithin(Incident.incident_location, ST_GeogFromText(point), radius_meters),
            )
        )
        return list(result.scalars().all())

    async def add_photo(
        self,
        db: AsyncSession,
        incident_id: int,
        storage_url: str,
        ai_result: Optional[dict] = None,
    ) -> IncidentPhoto:
        photo = IncidentPhoto(
            incident_id=incident_id,
            storage_url=storage_url,
            ai_detected_issue=ai_result.get("issue") if ai_result else None,
            ai_confidence_score=ai_result.get("confidence") if ai_result else None,
            ai_metadata=ai_result,
        )
        db.add(photo)
        await db.flush()
        await db.refresh(photo)
        return photo


crud_incident = CRUDIncident(Incident)
