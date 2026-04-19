"""
Endpoints de Bitácora / Audit (Admin) — /api/v1/audit
"""
from typing import List
from fastapi import APIRouter

from app.api.dependencies import AdminOnly, DBSession
from app.schemas.audit import AuditLogResponse
from sqlalchemy import select, desc
from app.models.audit_log import AuditLog

router = APIRouter(prefix="/audit", tags=["📜 Bitácora Administrativa"])


@router.get("", response_model=List[AuditLogResponse])
async def list_audit_logs(
    db: DBSession,
    admin_user: AdminOnly,
    skip: int = 0,
    limit: int = 100,
):
    """Retorna listado completo de registros de bitácora (Solo Admin)."""
    result = await db.execute(
        select(AuditLog).order_by(desc(AuditLog.created_at)).offset(skip).limit(limit)
    )
    logs = result.scalars().all()
    return logs
