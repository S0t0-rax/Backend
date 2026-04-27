"""
Endpoints de Talleres — /api/v1/workshops
Incluye búsqueda por proximidad geoespacial.
"""
from typing import List

from fastapi import APIRouter, Query

from app.api.dependencies import CurrentUser, DBSession, WorkshopOwnerOrAdmin
from app.crud.workshop import crud_workshop
from app.schemas.workshop import (
    NearbyWorkshopResponse,
    WorkshopCreate,
    WorkshopResponse,
    WorkshopUpdate,
)

router = APIRouter(prefix="/workshops", tags=["🔧 Talleres"])


@router.get("/", response_model=List[WorkshopResponse])
async def list_workshops(
    db: DBSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
):
    """Lista todos los talleres disponibles (público)."""
    return await crud_workshop.get_multi(db, skip=skip, limit=limit, only_available=True)


@router.get("/my-workshops", response_model=List[WorkshopResponse])
async def list_my_workshops(
    db: DBSession,
    current_user: WorkshopOwnerOrAdmin,
):
    """Lista todos los talleres del dueño autenticado (incluyendo inactivos)."""
    from sqlalchemy import select
    from app.models.workshop import Workshop
    
    stmt = select(Workshop).where(Workshop.owner_id == current_user.id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/nearby", response_model=List[NearbyWorkshopResponse])
async def nearby_workshops(
    db: DBSession,
    latitude: float = Query(..., ge=-90, le=90, description="Latitud del punto de búsqueda"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitud del punto de búsqueda"),
    radius_meters: float = Query(10000, ge=500, le=100000, description="Radio de búsqueda en metros"),
    limit: int = Query(20, le=50),
):
    """
    Talleres cercanos ordenados por distancia.

    Usa el índice GIST de PostGIS (idx_workshops_geom) con ST_DWithin + ST_Distance.
    Performance: O(log n) con índice espacial.
    """
    results = await crud_workshop.find_nearby(db, latitude, longitude, radius_meters, limit)
    return [
        NearbyWorkshopResponse(
            **WorkshopResponse.model_validate(w).model_dump(),
            distance_meters=round(dist, 2),
        )
        for w, dist in results
    ]


@router.post("/", response_model=WorkshopResponse, status_code=201)
async def create_workshop(
    data: WorkshopCreate, current_user: WorkshopOwnerOrAdmin, db: DBSession
):
    """Registra un nuevo taller. Solo owners y admins."""
    return await crud_workshop.create(db, obj_in=data, owner_id=current_user.id)


@router.get("/{workshop_id}", response_model=WorkshopResponse)
async def get_workshop(workshop_id: int, db: DBSession):
    """Detalle de un taller (público)."""
    from app.core.exceptions import NotFoundException
    w = await crud_workshop.get(db, workshop_id)
    if not w:
        raise NotFoundException("Taller")
    return w


@router.patch("/{workshop_id}", response_model=WorkshopResponse)
async def update_workshop(
    workshop_id: int,
    data: WorkshopUpdate,
    current_user: WorkshopOwnerOrAdmin,
    db: DBSession,
):
    """Actualiza un taller. Solo el dueño o admin."""
    from app.core.exceptions import NotFoundException, ForbiddenException
    w = await crud_workshop.get(db, workshop_id)
    if not w:
        raise NotFoundException("Taller")
    roles = {r.name for r in current_user.roles}
    if "admin" not in roles and w.owner_id != current_user.id:
        raise ForbiddenException("No tienes permiso para modificar este taller.")
    return await crud_workshop.update(db, db_obj=w, obj_in=data)


@router.delete("/{workshop_id}", status_code=204)
async def delete_workshop(
    workshop_id: int,
    current_user: WorkshopOwnerOrAdmin,
    db: DBSession,
):
    """Elimina un taller. Solo el dueño o admin."""
    from app.core.exceptions import NotFoundException, ForbiddenException
    w = await crud_workshop.get(db, workshop_id)
    if not w:
        raise NotFoundException("Taller")
        
    roles = {r.name for r in current_user.roles}
    if "admin" not in roles and w.owner_id != current_user.id:
        raise ForbiddenException("No tienes permiso para eliminar este taller.")
        
    await crud_workshop.delete(db, id=workshop_id)
    return None
