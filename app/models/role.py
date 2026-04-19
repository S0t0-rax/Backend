"""
Modelos: Role, UserRole (RBAC)
"""
from typing import TYPE_CHECKING, List

from sqlalchemy import BigInteger, Column, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User

# ── Tabla de asociación users ↔ roles ─────────────────────────
user_roles_table = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


class Role(Base):
    """
    Tabla `roles` — catálogo de roles del sistema.
    Valores: 'admin', 'workshop_owner', 'mechanic', 'client'
    """
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relación ───────────────────────────────────────────────
    users: Mapped[List["User"]] = relationship(
        "User",
        secondary="user_roles",
        back_populates="roles",
    )

    def __repr__(self) -> str:
        return f"<Role name={self.name}>"
