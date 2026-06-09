"""
Router principal API v1 — agrupa todos los módulos.
"""
from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.incidents import router as incidents_router
from app.api.v1.endpoints.workshops import router as workshops_router
from app.api.v1.endpoints.tenants import router as tenants_router
from app.api.v1.websockets.location import router as location_ws_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.users import router as users_router
from app.api.v1.endpoints.audit import router as audit_router
from app.api.v1.endpoints.cars import router as cars_router
from app.api.v1.endpoints.service_orders import router as service_orders_router
from app.api.v1.endpoints.payments import router as payments_router
from app.api.v1.endpoints.reports import router as reports_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(audit_router)
api_router.include_router(incidents_router)
api_router.include_router(workshops_router)
api_router.include_router(payments_router)
api_router.include_router(cars_router)
api_router.include_router(service_orders_router)
api_router.include_router(tenants_router, prefix="/tenants", tags=["Tenants"])
api_router.include_router(location_ws_router, prefix="/ws/location", tags=["WebSockets"])
api_router.include_router(reports_router)
