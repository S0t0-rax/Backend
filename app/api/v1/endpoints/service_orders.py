from typing import List
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select, update
from app.api.dependencies import CurrentUser, DBSession
from app.models.service_order import ServiceOrder
from app.models.user import User
from app.models.incident import Incident
from app.schemas.service_order import ServiceOrderResponse, ServiceOrderUpdate
from app.services.notification_service import notification_service
from datetime import datetime

router = APIRouter(prefix="/service-orders", tags=["🛠️ Órdenes de Servicio"])

@router.patch("/{order_id}", response_model=ServiceOrderResponse)
async def update_service_order(
    order_id: int,
    data: ServiceOrderUpdate,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Permite actualizar una orden de servicio.
    Los mecánicos pueden actualizar su arrival_status.
    """
    stmt = select(ServiceOrder).where(ServiceOrder.id == order_id)
    res = await db.execute(stmt)
    order = res.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Orden de servicio no encontrada.")
    
    # Validar permisos
    roles = {r.name for r in current_user.roles}
    is_admin = "admin" in roles
    is_owner = "workshop_owner" in roles
    is_assigned_mechanic = order.mechanic_id == current_user.id
    
    if not (is_admin or is_owner or is_assigned_mechanic):
        raise HTTPException(status_code=403, detail="No tienes permiso para modificar esta orden.")

    # Actualizar campos
    if data.arrival_status is not None:
        order.arrival_status = data.arrival_status
        # Si llega al lugar, marcamos started_at si no está marcado
        if data.arrival_status == "arrived" and not order.started_at:
            order.started_at = datetime.now()
            # Si no marcó salida, la marcamos igual o antes
            if not order.scheduled_at:
                order.scheduled_at = order.started_at
            
        # Si sale del taller, marcamos scheduled_at si no está marcado
        if data.arrival_status == "on_the_way" and not order.scheduled_at:
            if order.started_at:
                order.scheduled_at = order.started_at
            else:
                order.scheduled_at = datetime.now()
            
        # --- Notificación Push: Cambio de estado de llegada ---
        # Buscamos al cliente a través del incidente relacionado
        stmt_incident = select(Incident).where(Incident.id == order.incident_id)
        res_incident = await db.execute(stmt_incident)
        incident = res_incident.scalar_one_or_none()
        
        if incident:
            stmt_client = select(User).where(User.id == incident.client_id)
            res_client = await db.execute(stmt_client)
            client = res_client.scalar_one_or_none()
            
            if client and client.fcm_token:
                if data.arrival_status == "on_the_way":
                    await notification_service.notify_status_change(
                        user_token=client.fcm_token,
                        status_type="mechanic_on_the_way",
                        details={"eta": "15-20"} # Valor por defecto, se podría calcular
                    )
                elif data.arrival_status == "arrived":
                    await notification_service.notify_status_change(
                        user_token=client.fcm_token,
                        status_type="mechanic_arrived"
                    )
            
    if data.final_cost is not None:
        order.final_cost = data.final_cost
        
    if data.finished_at is not None:
        order.finished_at = data.finished_at

    db.add(order)
    await db.commit()
    await db.refresh(order)
    return order
