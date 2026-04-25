"""
CRUD de Incidente con soporte geoespacial.
"""
from typing import List, Optional

from geoalchemy2.functions import ST_GeogFromText, ST_DWithin, ST_Distance
from geoalchemy2.elements import WKTElement
from sqlalchemy import select, func, text
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.incident import Incident, IncidentPhoto
from app.models.service_order import ServiceOrder
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
        from loguru import logger
        
        try:
            point_wkt = f"POINT({obj_in.longitude} {obj_in.latitude})"
            logger.debug(f"Creando incidente para cliente {client_id} en {point_wkt}")
            
            incident = Incident(
                client_id=client_id,
                car_id=obj_in.car_id,
                incident_location=WKTElement(point_wkt, srid=4326),
                address_reference=obj_in.address_reference,
                description=obj_in.description,
                severity_level="low",
                status="open"
            )
            
            db.add(incident)
            await db.flush()
            await db.refresh(incident)

            # Si el cliente escogió un taller, creamos la orden de servicio inmediatamente
            if obj_in.workshop_id and obj_in.workshop_id > 0:
                logger.debug(f"Asignando taller {obj_in.workshop_id} al incidente {incident.id}")
                service_order = ServiceOrder(
                    incident_id=incident.id,
                    workshop_id=obj_in.workshop_id,
                    arrival_status="pending"
                )
                db.add(service_order)
                await db.flush()

            incident.photos = []  # Evita el error de carga diferida (lazy load)
            return incident
        except Exception as e:
            logger.error(f"Error en CRUDIncident.create: {e}")
            raise e


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

    async def get_all_incidents_with_details(self, db: AsyncSession) -> List[dict]:
        """
        Retorna todos los incidentes con información del cliente y del mecánico asignado.
        Ideal para el panel de monitoreo global del administrador.
        """
        from app.models.user import User
        from app.models.service_order import ServiceOrder
        from app.models.workshop import Workshop
        from sqlalchemy.orm import aliased

        Mechanic = aliased(User)
        
        result = await db.execute(
            select(
                Incident,
                User.full_name.label("client_name"),
                Mechanic.full_name.label("mechanic_name"),
                Workshop.name.label("workshop_name")
            )
            .join(User, Incident.client_id == User.id)
            .outerjoin(ServiceOrder, Incident.id == ServiceOrder.incident_id)
            .outerjoin(Mechanic, ServiceOrder.mechanic_id == Mechanic.id)
            .outerjoin(Workshop, ServiceOrder.workshop_id == Workshop.id)
            .order_by(Incident.reported_at.desc())
        )

        incidents_data = []
        for row in result.all():
            inc, c_name, m_name, w_name = row
            # Convertimos el objeto SQLAlchemy a un diccionario compatible con el schema
            # Ojo: IncidentResponse espera 'photos', así que las cargamos si es necesario
            # Para el monitoreo global igual no necesitamos todas las fotos, pero por consistencia:
            data = {
                "id": inc.id,
                "client_id": inc.client_id,
                "car_id": inc.car_id,
                "address_reference": inc.address_reference,
                "description": inc.description,
                "severity_level": inc.severity_level,
                "status": inc.status,
                "reported_at": inc.reported_at,
                "latitude": inc.latitude,  # Crucial: extraído vía propiedad del modelo
                "longitude": inc.longitude, # Crucial: extraído vía propiedad del modelo
                "client_name": c_name,
                "mechanic_name": m_name,
                "workshop_name": w_name,
                "photos": [] # Simplificamos para no sobrecargar el dashboard global
            }
            incidents_data.append(data)
        
        return incidents_data



crud_incident = CRUDIncident(Incident)
