"""
Router principal API v1 — agrupa todos los módulos.
"""
from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.incidents import router as incidents_router
from app.api.v1.endpoints.workshops import router as workshops_router
from app.api.v1.endpoints.payments import router as payments_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.users import router as users_router
from app.api.v1.endpoints.audit import router as audit_router
from app.api.v1.endpoints.cars import router as cars_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(audit_router)
api_router.include_router(incidents_router)
api_router.include_router(workshops_router)
api_router.include_router(payments_router)
api_router.include_router(cars_router)

