"""
Paquete models — exporta todos los modelos del sistema.
Esto garantiza que Alembic los detecte automáticamente
al hacer `from app.models import *` en alembic/env.py
"""
from app.models.base import Base, TimestampMixin
from app.models.role import Role, user_roles_table
from app.models.user import User
from app.models.workshop import Workshop, workshop_staff_table
from app.models.car import Car
from app.models.incident import Incident, IncidentPhoto
from app.models.services_catalog import ServicesCatalog
from app.models.service_order import ServiceOrder
from app.models.payment import Payment, PaymentMethod, TaxData, Invoice
from app.models.status_history import StatusHistory
from app.models.audit_log import AuditLog

__all__ = [
    "Base", "TimestampMixin",
    "Role", "user_roles_table",
    "User",
    "Workshop", "workshop_staff_table",
    "Car",
    "Incident", "IncidentPhoto",
    "ServicesCatalog",
    "ServiceOrder",
    "Payment", "PaymentMethod", "TaxData", "Invoice",
    "StatusHistory",
    "AuditLog",
]
