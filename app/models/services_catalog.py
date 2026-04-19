"""
Modelo: ServicesCatalog — catálogo de servicios mecánicos.
"""
from typing import Optional
from decimal import Decimal

from sqlalchemy import Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ServicesCatalog(Base):
    """Tabla `services_catalog` — servicios ofrecidos."""
    __tablename__ = "services_catalog"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    base_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)

    def __repr__(self) -> str:
        return f"<ServicesCatalog id={self.id} name={self.name}>"
