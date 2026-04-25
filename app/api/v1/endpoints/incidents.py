"""
Endpoints de Incidentes — /api/v1/incidents
Incluye: reporte, subida de fotos con análisis IA, búsqueda por proximidad.
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, File, Query, UploadFile

from app.api.dependencies import AdminOnly, AnyStaff, CurrentUser, DBSession
from app.crud.incident import crud_incident
from app.schemas.incident import IncidentCreate, IncidentResponse, IncidentUpdate, IncidentGlobalResponse
from app.services.ai_service import ai_service

router = APIRouter(prefix="/incidents", tags=["🚨 Incidentes"])


@router.post("/", response_model=IncidentResponse, status_code=201)
async def report_incident(
    data: IncidentCreate, current_user: CurrentUser, db: DBSession
):
    """
    Reporta un nuevo incidente vehicular con ubicación GPS.
    La localización se almacena como GEOGRAPHY(POINT, 4326) en PostGIS.
    """
    from loguru import logger
    try:
        incident = await crud_incident.create(db, obj_in=data, client_id=current_user.id)
        return incident
    except Exception as e:
        logger.exception(f"Error al reportar incidente: {e}")
        raise e


@router.get("/", response_model=List[IncidentResponse])
async def list_my_incidents(
    current_user: CurrentUser,
    db: DBSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
):
    """Lista los incidentes del cliente autenticado."""
    return await crud_incident.get_by_client(db, current_user.id, skip=skip, limit=limit)


@router.get("/global", response_model=List[IncidentGlobalResponse])
async def list_global_incidents(
    db: DBSession,
    _: AdminOnly,
):
    """
    Lista todos los incidentes del sistema con detalles de mecánicos asignados.
    Solo accesible por administradores.
    """
    return await crud_incident.get_all_incidents_with_details(db)


@router.get("/nearby", response_model=List[IncidentResponse])
async def nearby_incidents(
    db: DBSession,
    _: AnyStaff,
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_meters: float = Query(5000, ge=100, le=50000),
):
    """
    Busca incidentes abiertos en el radio dado.
    Usa el índice GIST de PostGIS: idx_incidents_location para performance.
    Solo accesible por staff (admin, workshop_owner, mechanic).
    """
    return await crud_incident.find_nearby(db, latitude, longitude, radius_meters)


@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(incident_id: int, current_user: CurrentUser, db: DBSession):
    """Detalle de un incidente con sus fotos."""
    from app.core.exceptions import NotFoundException
    incident = await crud_incident.get_with_photos(db, incident_id)
    if not incident:
        raise NotFoundException("Incidente")
    return incident


@router.patch("/{incident_id}", response_model=IncidentResponse)
async def update_incident(
    incident_id: int, data: IncidentUpdate, _: AnyStaff, db: DBSession
):
    """Actualiza estado/diagnóstico del incidente. Solo staff."""
    from app.core.exceptions import NotFoundException
    from app.models.status_history import StatusHistory

    incident = await crud_incident.get(db, incident_id)
    if not incident:
        raise NotFoundException("Incidente")

    old_status = incident.status
    updated = await crud_incident.update(db, db_obj=incident, obj_in=data)

    # Auditoría automática de cambio de estado
    if data.status and data.status != old_status:
        history = StatusHistory(
            incident_id=incident_id,
            old_status=old_status,
            new_status=data.status,
        )
        db.add(history)
        await db.flush()

    return updated


@router.post("/{incident_id}/photos", response_model=IncidentResponse)
async def upload_incident_photo(
    incident_id: int,
    current_user: CurrentUser,
    db: DBSession,
    file: UploadFile = File(..., description="Foto del incidente (JPG/PNG)"),
):
    """
    Sube una foto del incidente.

    Flujo automático:
    1. Valida el archivo
    2. Sube a AWS S3
    3. Envía a la API de IA para análisis de daños
    4. Guarda URL + resultado IA en incident_photos
    """
    from app.core.exceptions import NotFoundException, BadRequestException

    incident = await crud_incident.get(db, incident_id)
    if not incident:
        raise NotFoundException("Incidente")

    if not file.content_type.startswith("image/"):
        raise BadRequestException("Solo se aceptan archivos de imagen.")

    image_bytes = await file.read()
    filename = f"{incident_id}/{uuid.uuid4().hex}_{file.filename}"

    # 1. Subir a S3
    storage_url = await ai_service.upload_image_to_s3(
        image_bytes, filename, file.content_type
    )

    # 2. Analizar con IA
    ai_result = await ai_service.analyze_vehicle_damage(storage_url)

    # 3. Guardar en BD
    await crud_incident.add_photo(db, incident_id, storage_url, ai_result)

    return await crud_incident.get_with_photos(db, incident_id)
