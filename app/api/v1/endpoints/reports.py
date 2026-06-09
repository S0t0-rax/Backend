from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from datetime import datetime
from typing import Optional

from app.api.dependencies import DBSession, CurrentUser, AdminOnly
from app.crud.incident import crud_incident
from app.services.report_service import report_service
from app.core.exceptions import ForbiddenException

router = APIRouter(prefix="/reports", tags=["📈 Reportes"])

@router.get("/incidents/excel")
async def get_incidents_excel(
    db: DBSession,
    current_user: CurrentUser,
    status: Optional[str] = None,
    start_date: Optional[str] = None, # Formato YYYY-MM-DD
    end_date: Optional[str] = None
):
    """
    Descarga reporte en Excel de los incidentes.
    Filtra por taller si el usuario es owner. Si es admin, ve todos.
    """
    roles = {r.name for r in current_user.roles}
    is_admin = "admin" in roles
    is_owner = "workshop_owner" in roles
    
    if not is_admin and not is_owner:
        raise ForbiddenException("No tienes permiso para generar reportes.")

    owner_id = current_user.id if is_owner and not is_admin else None
    
    data = await crud_incident.get_client_incidents_with_details(
        db, client_id=None, owner_id=owner_id
    )

    # Filtrado local por simplicidad y robustez
    if status:
        data = [d for d in data if d["status"] == status]
    if start_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        data = [d for d in data if d["reported_at"] and d["reported_at"].date() >= start_dt]
    if end_date:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        data = [d for d in data if d["reported_at"] and d["reported_at"].date() <= end_dt]

    excel_file = report_service.generate_incidents_excel(data)
    
    filename = f"reporte_servicios_{datetime.now().strftime('%Y%m%d')}.xlsx"
    headers = {
        'Content-Disposition': f'attachment; filename="{filename}"'
    }
    
    return StreamingResponse(
        excel_file, 
        headers=headers, 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@router.get("/incidents/pdf")
async def get_incidents_pdf(
    db: DBSession,
    current_user: CurrentUser,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    Descarga reporte en PDF.
    """
    roles = {r.name for r in current_user.roles}
    is_admin = "admin" in roles
    is_owner = "workshop_owner" in roles
    
    if not is_admin and not is_owner:
        raise ForbiddenException("No tienes permiso para generar reportes.")

    owner_id = current_user.id if is_owner and not is_admin else None
    
    data = await crud_incident.get_client_incidents_with_details(
        db, client_id=None, owner_id=owner_id
    )

    if status:
        data = [d for d in data if d["status"] == status]
    if start_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        data = [d for d in data if d["reported_at"] and d["reported_at"].date() >= start_dt]
    if end_date:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        data = [d for d in data if d["reported_at"] and d["reported_at"].date() <= end_dt]

    title = "Reporte Global de Servicios" if is_admin else f"Reporte de Taller ({current_user.full_name})"
    pdf_file = report_service.generate_incidents_pdf(title, data)
    
    filename = f"reporte_servicios_{datetime.now().strftime('%Y%m%d')}.pdf"
    headers = {
        'Content-Disposition': f'attachment; filename="{filename}"'
    }
    
    return StreamingResponse(
        pdf_file, 
        headers=headers, 
        media_type="application/pdf"
    )
