"""
Modelo: Car (cars) — Vehículos de los clientes.
"""
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import BigInteger, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.incident import Incident


class Car(Base):
    """Tabla `cars` — vehículos registrados por los clientes."""

    __tablename__ = "cars"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    license_plate: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    brand: Mapped[str] = mapped_column(String(50), nullable=False)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    # ── Relaciones ─────────────────────────────────────────────
    owner: Mapped["User"] = relationship("User", back_populates="cars")
    incidents: Mapped[List["Incident"]] = relationship("Incident", back_populates="car")

    def __repr__(self) -> str:
        return f"<Car plate={self.license_plate} {self.brand} {self.model}>"
