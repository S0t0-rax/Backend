"""
Endpoints de Vehículos — /api/v1/cars
"""
from typing import List
from fastapi import APIRouter, HTTPException, Query

from app.api.dependencies import CurrentUser, DBSession
from app.crud.car import crud_car
from app.schemas.car import CarCreate, CarResponse, CarUpdate

router = APIRouter(prefix="/cars", tags=["🚗 Vehículos"])


@router.post("/", response_model=CarResponse, status_code=201)
async def create_car(
    data: CarCreate, 
    current_user: CurrentUser, 
    db: DBSession
):
    """Registra un nuevo vehículo para el cliente autenticado."""
    # Verificar si la placa ya existe
    existing = await crud_car.get_by_plate(db, data.license_plate)
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"La placa {data.license_plate} ya está registrada."
        )
    
    return await crud_car.create_with_owner(db, obj_in=data, owner_id=current_user.id)


@router.get("/", response_model=List[CarResponse])
async def list_my_cars(
    current_user: CurrentUser,
    db: DBSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
):
    """Lista todos los vehículos vinculados al cliente."""
    return await crud_car.get_by_owner(db, owner_id=current_user.id, skip=skip, limit=limit)


@router.get("/{car_id}", response_model=CarResponse)
async def get_car(
    car_id: int,
    current_user: CurrentUser,
    db: DBSession
):
    """Obtiene detalles de un vehículo específico."""
    car = await crud_car.get(db, car_id)
    if not car or car.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado.")
    return car


@router.put("/{car_id}", response_model=CarResponse)
async def update_car(
    car_id: int,
    data: CarUpdate,
    current_user: CurrentUser,
    db: DBSession
):
    """Actualiza la información de un vehículo."""
    car = await crud_car.get(db, car_id)
    if not car or car.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado.")
    
    return await crud_car.update(db, db_obj=car, obj_in=data)


@router.delete("/{car_id}", status_code=204)
async def delete_car(
    car_id: int,
    current_user: CurrentUser,
    db: DBSession
):
    """Elimina un vehículo del perfil del cliente."""
    car = await crud_car.get(db, car_id)
    if not car or car.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado.")
    
    await crud_car.delete(db, id=car_id)
    return None
