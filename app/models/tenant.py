from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import BigInteger, Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.workshop import Workshop
    from app.models.incident import Incident

class Tenant(Base):
    """
    Tabla `tenants` — Representa una organización o empresa automotriz independiente.
    Es el pilar de la arquitectura Multi-Tenant.
    """
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    tax_id: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True, comment="NIT o RUC de la empresa")
    subdomain: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True, comment="Subdominio para el panel web")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # ── Relaciones Multi-Tenant ────────────────────────────────────────
    users: Mapped[List["User"]] = relationship(
        "User", back_populates="tenant", cascade="all, delete-orphan"
    )
    workshops: Mapped[List["Workshop"]] = relationship(
        "Workshop", back_populates="tenant", cascade="all, delete-orphan"
    )
    incidents: Mapped[List["Incident"]] = relationship(
        "Incident", back_populates="tenant", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Tenant id={self.id} name={self.name}>"
