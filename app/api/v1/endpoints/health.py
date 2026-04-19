"""
Endpoints de Health Check — /api/v1/health
"""
from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.api.dependencies import DBSession

router = APIRouter(prefix="/health", tags=["🏥 Sistema"])


@router.get("/")
async def health_check(db: DBSession):
    """
    Health check del sistema:
    - Estado de la API
    - Estado de la BD (PostgreSQL)
    - Versión de PostGIS
    """
    db_status = "ok"
    postgis_version = "N/A"

    try:
        await db.execute(text("SELECT 1"))
        result = await db.execute(text("SELECT PostGIS_Version()"))
        postgis_version = result.scalar()
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "database": db_status,
        "postgis_version": postgis_version,
    }
