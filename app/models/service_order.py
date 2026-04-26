"""
Modelo: ServiceOrder (service_orders) — Órdenes de Trabajo.
Incluye tracking de ubicación del mecánico con PostGIS.
"""
from typing import TYPE_CHECKING, Optional
from datetime import datetime
from decimal import Decimal

from geoalchemy2 import Geography
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.incident import Incident
    from app.models.user import User
    from app.models.workshop import Workshop
    from app.models.services_catalog import ServicesCatalog
    from app.models.payment import Payment


class ServiceOrder(Base):
    """
    Tabla `service_orders` — orden de trabajo asociada a un incidente.

    - Tracking en tiempo real: current_mechanic_location GEOGRAPHY(POINT)
    - Ciclo de vida (arrival_status): pending → on_the_way → arrived
    - Ciclo de vida (incidents): open → assigned → in_progress → resolved | cancelled
    """
    __tablename__ = "service_orders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    incident_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("incidents.id"), unique=True, nullable=True
    )
    mechanic_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True
    )
    workshop_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("workshops.id"), nullable=True
    )
    service_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("services_catalog.id"), nullable=True
    )

    # ── Timestamps de la orden ─────────────────────────────────
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Costos ─────────────────────────────────────────────────
    estimated_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    final_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)

    arrival_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # ── Campo PostGIS — Tracking del mecánico ─────────────────
    current_mechanic_location = Column(
        Geography(geometry_type="POINT", srid=4326),
        nullable=True,
        comment="Ubicación GPS del mecánico en ruta al incidente",
    )

    # ── Relaciones ─────────────────────────────────────────────
    incident: Mapped[Optional["Incident"]] = relationship(
        "Incident", back_populates="service_order"
    )
    mechanic: Mapped[Optional["User"]] = relationship("User", foreign_keys=[mechanic_id])
    workshop: Mapped[Optional["Workshop"]] = relationship("Workshop", back_populates="service_orders")
    service: Mapped[Optional["ServicesCatalog"]] = relationship("ServicesCatalog")
    payment: Mapped[Optional["Payment"]] = relationship(
        "Payment", back_populates="service_order", uselist=False
    )

    def __repr__(self) -> str:
        return f"<ServiceOrder id={self.id} incident={self.incident_id}>"
