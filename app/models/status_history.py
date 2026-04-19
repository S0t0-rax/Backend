"""
Modelo: StatusHistory — auditoría de cambios de estado en incidentes.
"""
from typing import Optional
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base


class StatusHistory(Base):
    """
    Tabla `status_history` — trazabilidad de cambios de estado.
    Registra cada transición de estado de un incidente.
    """
    __tablename__ = "status_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    incident_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("incidents.id"), nullable=True
    )
    old_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    new_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    changed_by: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # ── Relaciones ─────────────────────────────────────────────
    incident = relationship("Incident", back_populates="status_history")
