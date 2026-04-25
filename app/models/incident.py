"""
Modelos: Incident + IncidentPhoto
- `Incident`: incluye `incident_location` GEOGRAPHY(POINT, 4326)
- `IncidentPhoto`: incluye campos de análisis de IA (JSONB)
"""
from typing import TYPE_CHECKING, List, Optional
from datetime import datetime

from geoalchemy2 import Geography
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.car import Car
    from app.models.service_order import ServiceOrder
    from app.models.status_history import StatusHistory


class Incident(Base):
    """
    Tabla `incidents` — incidentes vehiculares reportados.

    Flujo de estados:
        open → assigned → resolved | cancelled

    Campo PostGIS: incident_location GEOGRAPHY(POINT, 4326)
    """
    __tablename__ = "incidents"
    __allow_unmapped__ = True # Permitir atributos anotados no mapeados (como _latitude)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    client_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True
    )
    car_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("cars.id"), nullable=True
    )

    # ── Campo PostGIS ──────────────────────────────────────────
    incident_location = Column(
        Geography(geometry_type="POINT", srid=4326),
        nullable=False,
        comment="Coordenadas GPS donde ocurrió el incidente",
    )

    address_reference: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    severity_level: Mapped[str] = mapped_column(String(20), default="unknown", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="open", nullable=False)
    reported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # ── Relaciones ─────────────────────────────────────────────
    client: Mapped[Optional["User"]] = relationship(
        "User", back_populates="incidents", foreign_keys=[client_id]
    )
    car: Mapped[Optional["Car"]] = relationship("Car", back_populates="incidents")
    photos: Mapped[List["IncidentPhoto"]] = relationship(
        "IncidentPhoto", back_populates="incident", cascade="all, delete-orphan"
    )
    service_order: Mapped[Optional["ServiceOrder"]] = relationship(
        "ServiceOrder", back_populates="incident", uselist=False
    )
    status_history: Mapped[List["StatusHistory"]] = relationship(
        "StatusHistory", back_populates="incident"
    )

    def __repr__(self) -> str:
        return f"<Incident id={self.id} status={self.status}>"

    # ── Atributos de instancia para evitar errores de greenlet/async ──
    _latitude: Optional[float] = None
    _longitude: Optional[float] = None

    @property
    def latitude(self) -> float:
        """Extrae latitud desde el objeto Geography o caché temporal."""
        if self._latitude is not None:
            return self._latitude
            
        loc = self.incident_location
        if loc is not None:
            try:
                from geoalchemy2.shape import to_shape
                # Si es un elemento ya procesado o WKB
                point = to_shape(loc)
                return point.y
            except Exception:
                return 0.0
        return 0.0

    @property
    def longitude(self) -> float:
        """Extrae longitud desde el objeto Geography o caché temporal."""
        if self._longitude is not None:
            return self._longitude
            
        loc = self.incident_location
        if loc is not None:
            try:
                from geoalchemy2.shape import to_shape
                point = to_shape(loc)
                return point.x
            except Exception:
                return 0.0
        return 0.0


class IncidentPhoto(Base):
    """
    Tabla `incident_photos` — fotos del incidente con metadatos de IA.

    Campos de IA:
        - ai_detected_issue: problema detectado por el modelo de visión
        - ai_confidence_score: confianza del modelo (0.00 - 100.00)
        - ai_metadata: JSON con detalles técnicos del análisis
    """
    __tablename__ = "incident_photos"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    incident_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False
    )
    storage_url: Mapped[str] = mapped_column(Text, nullable=False, comment="URL en S3 / storage")

    # ── Campos IA ──────────────────────────────────────────────
    ai_detected_issue: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ai_confidence_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    # JSONB: almacena el payload completo de respuesta del modelo de visión
    ai_metadata = Column(JSON, nullable=True, comment="Payload JSON del modelo de IA")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # ── Relaciones ─────────────────────────────────────────────
    incident: Mapped["Incident"] = relationship("Incident", back_populates="photos")

    def __repr__(self) -> str:
        return f"<IncidentPhoto id={self.id} incident_id={self.incident_id}>"
