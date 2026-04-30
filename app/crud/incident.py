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
                status="open",
                reported_at=func.now()
            )
            # Cacheamos para evitar el error de greenlet/IO durante la serialización
            incident._latitude = obj_in.latitude
            incident._longitude = obj_in.longitude
            
            db.add(incident)
            await db.flush()

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

            # Retornamos el esquema de respuesta directamente para evitar fallos de serialización ORM (greenlet error)
            from app.schemas.incident import IncidentResponse
            return IncidentResponse(
                id=incident.id,
                client_id=incident.client_id,
                car_id=incident.car_id,
                address_reference=incident.address_reference,
                description=incident.description,
                severity_level=incident.severity_level,
                status=incident.status,
                reported_at=incident.reported_at,
                latitude=obj_in.latitude,
                longitude=obj_in.longitude,
                photos=[]
            )
        except Exception as e:
            logger.error(f"Error en CRUDIncident.create: {e}")
            raise e


    async def find_nearby(
        self,
        db: AsyncSession,
        latitude: float,
        longitude: float,
        radius_meters: float = 5000,
        status: Optional[str] = "open",
        owner_id: Optional[int] = None
    ) -> List[Incident]:
        """
        Busca incidentes. Si el radio es > 0, filtra por cercanía.
        Filtra para que solo el taller preferido (o todos si no hay preferencia) pueda verlo.
        """
        from app.models.service_order import ServiceOrder
        from app.models.workshop import Workshop
        
        query = select(Incident).outerjoin(ServiceOrder, Incident.id == ServiceOrder.incident_id)
        
        if status:
            query = query.where(Incident.status == status)
        
        # Filtrado de taller preferencial
        if owner_id:
            query = query.outerjoin(Workshop, ServiceOrder.workshop_id == Workshop.id)
            # Un incidente es visible si:
            # 1. No tiene ServiceOrder (es para "Cualquiera")
            # 2. Tiene ServiceOrder y el taller pertenece al owner_id actual
            from sqlalchemy import or_
            query = query.where(
                or_(
                    ServiceOrder.id.is_(None),
                    ServiceOrder.workshop_id.is_(None),
                    Workshop.owner_id == owner_id
                )
            )

        # Si el radio es mayor a 0, aplicamos el filtro de PostGIS
        if radius_meters > 0:
            point = f"SRID=4326;POINT({longitude} {latitude})"
            query = query.where(
                ST_DWithin(Incident.incident_location, ST_GeogFromText(point), radius_meters)
            )
        
        result = await db.execute(query.order_by(Incident.reported_at.desc()))
        db_incidents = list(result.scalars().all())
        
        # DEBUG: Contar cuántos hay realmente en la DB para diagnosticar
        from loguru import logger
        total_result = await db.execute(select(func.count(Incident.id)))
        total_count = total_result.scalar_one()
        logger.debug(f"Búsqueda cercana: Encontrados {len(db_incidents)} abiertos de un total de {total_count} incidentes en DB.")

        # Retornamos los esquemas directamente para evitar errores de greenlet/lazy load
        from app.schemas.incident import IncidentResponse
        return [
            IncidentResponse(
                id=inc.id,
                client_id=inc.client_id,
                car_id=inc.car_id,
                address_reference=inc.address_reference,
                description=inc.description,
                severity_level=inc.severity_level,
                status=inc.status,
                reported_at=inc.reported_at,
                latitude=inc.latitude, # Accedemos aquí que estamos en el contexto asíncrono
                longitude=inc.longitude,
                photos=[]
            )
            for inc in db_incidents
        ]

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

    async def get_by_workshop_owner(self, db: AsyncSession, owner_id: int) -> List[dict]:
        """Retorna incidentes asignados a talleres del owner con detalles completos."""
        return await self.get_client_incidents_with_details(db, None, owner_id=owner_id)


    async def get_client_incidents_with_details(
        self, 
        db: AsyncSession, 
        client_id: Optional[int], 
        mechanic_id: Optional[int] = None,
        owner_id: Optional[int] = None
    ) -> List[dict]:
        """Retorna incidentes con info de quién le atiende, filtrado por cliente, mecánico o dueño."""
        from app.models.user import User
        from app.models.service_order import ServiceOrder
        from app.models.workshop import Workshop
        from sqlalchemy.orm import aliased

        Mechanic = aliased(User)
        
        query = (
            select(
                Incident,
                Mechanic.full_name.label("mechanic_name"),
                Workshop.name.label("workshop_name"),
                ServiceOrder.id.label("so_id"),
                ServiceOrder.arrival_status,
                ServiceOrder.scheduled_at,
                ServiceOrder.started_at,
                ServiceOrder.finished_at
            )
            .outerjoin(ServiceOrder, Incident.id == ServiceOrder.incident_id)
            .outerjoin(Mechanic, ServiceOrder.mechanic_id == Mechanic.id)
            .outerjoin(Workshop, ServiceOrder.workshop_id == Workshop.id)
        )
        
        if client_id:
            query = query.where(Incident.client_id == client_id)
        if mechanic_id:
            query = query.where(ServiceOrder.mechanic_id == mechanic_id)
            query = query.where(Incident.status.in_(["assigned", "in_progress"]))
        if owner_id:
            query = query.where(Workshop.owner_id == owner_id)
            query = query.where(Incident.status.in_(["assigned", "in_progress"]))
            
        result = await db.execute(query.order_by(Incident.reported_at.desc()))

        results = []
        for row in result.all():
            # Usar acceso por nombre para evitar errores de posición
            inc = row.Incident
            m_name = row.mechanic_name
            w_name = row.workshop_name
            so_id = row.so_id
            a_status = row.arrival_status
            s_at = row.scheduled_at
            st_at = row.started_at
            f_at = row.finished_at
            data = {
                "id": inc.id,
                "service_order_id": so_id,
                "scheduled_at": s_at,
                "started_at": st_at,
                "finished_at": f_at,
                "client_id": inc.client_id,
                "car_id": inc.car_id,
                "address_reference": inc.address_reference,
                "description": inc.description,
                "severity_level": inc.severity_level,
                "status": inc.status,
                "reported_at": inc.reported_at,
                "latitude": inc.latitude,
                "longitude": inc.longitude,
                "workshop_name": w_name,
                "mechanic_name": m_name,
                "arrival_status": a_status,
                "photos": [] 
            }
            results.append(data)
        
        return results

crud_incident = CRUDIncident(Incident)
