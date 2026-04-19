"""
Modelo: Workshop (workshops) + WorkshopStaff
Incluye campo geoespacial `geom` GEOGRAPHY(POINT, 4326).
"""
from typing import TYPE_CHECKING, List, Optional
from decimal import Decimal

from geoalchemy2 import Geography
from sqlalchemy import BigInteger, Column, ForeignKey, Numeric, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.service_order import ServiceOrder


# ── Tabla de asociación workshops ↔ mechanics ─────────────────
workshop_staff_table = Table(
    "workshop_staff",
    Base.metadata,
    Column("workshop_id", BigInteger, ForeignKey("workshops.id", ondelete="CASCADE"), primary_key=True),
    Column("mechanic_id", BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("specialty", String(100), nullable=True),
)


class Workshop(Base):
    """
    Tabla `workshops` — talleres mecánicos registrados.
    Campo PostGIS: geom GEOGRAPHY(POINT, 4326)
    """
    __tablename__ = "workshops"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    owner_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    tax_id: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True,
                                                   comment="NIT en Bolivia")
    address_text: Mapped[str] = mapped_column(Text, nullable=False)

    # ── Campo PostGIS ──────────────────────────────────────────
    # Ubicación exacta del taller en el mapa
    geom = Column(
        Geography(geometry_type="POINT", srid=4326),
        nullable=False,
        comment="Ubicación geográfica del taller (WGS84)",
    )

    rating: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2), default=5.0)

    # ── Relaciones ─────────────────────────────────────────────
    owner: Mapped[Optional["User"]] = relationship(
        "User", back_populates="owned_workshops", foreign_keys=[owner_id]
    )
    mechanics: Mapped[List["User"]] = relationship(
        "User",
        secondary="workshop_staff",
        lazy="selectin",
    )
    service_orders: Mapped[List["ServiceOrder"]] = relationship(
        "ServiceOrder", back_populates="workshop"
    )

    def __repr__(self) -> str:
        return f"<Workshop id={self.id} name={self.name}>"
