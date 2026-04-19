"""
Modelo: AuditLog (Bitácora) — Registro centralizado de auditoría.
"""
from typing import Optional
from datetime import datetime

from sqlalchemy import Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import Base

class AuditLog(Base):
    """
    Tabla `audit_logs` — Bitácora de acciones del sistema.
    """
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True) # Usamos JSONB nativo de postgres
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Relación
    user = relationship("User", backref="audit_logs")
