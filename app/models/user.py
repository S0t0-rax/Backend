"""
Modelo: User (users)
Incluye campo espacial `current_location` mediante GeoAlchemy2.
"""
from typing import TYPE_CHECKING, List, Optional

from geoalchemy2 import Geography
from sqlalchemy import BigInteger, Boolean, Column, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship


from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.role import Role
    from app.models.workshop import Workshop
    from app.models.car import Car
    from app.models.incident import Incident


class User(Base, TimestampMixin):
    """
    Tabla `users` — identidad del sistema.

    Roles soportados: admin | workshop_owner | mechanic | client
    Campo PostGIS: current_location GEOGRAPHY(POINT, 4326)
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # ── Campo Geoespacial (PostGIS) ───────────────────────────
    # Ubicación en tiempo real del mecánico o cliente
    # GEOGRAPHY(POINT, 4326) → WGS84 (lat/lng estándar GPS)
    current_location = Column(
        Geography(geometry_type="POINT", srid=4326),
        nullable=True,
        comment="Ubicación GPS en tiempo real (WGS84)",
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ── Relaciones ─────────────────────────────────────────────
    roles: Mapped[List["Role"]] = relationship(
        "Role",
        secondary="user_roles",
        back_populates="users",
        lazy="selectin",
    )
    owned_workshops: Mapped[List["Workshop"]] = relationship(
        "Workshop", back_populates="owner", foreign_keys="Workshop.owner_id"
    )
    cars: Mapped[List["Car"]] = relationship("Car", back_populates="owner")
    incidents: Mapped[List["Incident"]] = relationship(
        "Incident", back_populates="client", foreign_keys="Incident.client_id"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"
