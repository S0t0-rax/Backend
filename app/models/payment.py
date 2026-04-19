"""
Modelos: Payment, PaymentMethod, TaxData, Invoice.
Módulo financiero completo con soporte QR y facturación SIN Bolivia.
"""
from typing import TYPE_CHECKING, Optional
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.service_order import ServiceOrder


class PaymentMethod(Base):
    """Tabla `payment_methods` — métodos de pago disponibles."""
    __tablename__ = "payment_methods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False,
                                       comment="QR | Transferencia | Efectivo")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Payment(Base):
    """
    Tabla `payments` — registro de pagos.

    Soporte QR interoperable Bolivia:
        - transaction_id: ID único de la transacción en la pasarela
        - qr_code_image: URL del QR generado
    """
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    service_order_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("service_orders.id"), unique=True, nullable=True
    )
    payment_method_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("payment_methods.id"), nullable=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="BOB", nullable=False)

    # ── QR interoperable ───────────────────────────────────────
    transaction_id: Mapped[Optional[str]] = mapped_column(Text, unique=True, nullable=True)
    qr_code_image: Mapped[Optional[str]] = mapped_column(Text, nullable=True,
                                                          comment="URL del QR generado")
    payment_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)

    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # ── Relaciones ─────────────────────────────────────────────
    service_order: Mapped[Optional["ServiceOrder"]] = relationship(
        "ServiceOrder", back_populates="payment"
    )
    invoice: Mapped[Optional["Invoice"]] = relationship(
        "Invoice", back_populates="payment", uselist=False
    )
    payment_method: Mapped[Optional["PaymentMethod"]] = relationship("PaymentMethod")


class TaxData(Base):
    """Tabla `tax_data` — datos fiscales de los usuarios (NIT Bolivia)."""
    __tablename__ = "tax_data"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    nit_number: Mapped[str] = mapped_column(String(50), nullable=False)
    business_name: Mapped[str] = mapped_column(String(150), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Invoice(Base):
    """
    Tabla `invoices` — facturas electrónicas según normativa SIN Bolivia.

    Campos especiales:
        - cuf:  Código Único de Factura (Facturación en Línea)
        - cufd: Código Único de Facturación Diaria
        - control_code: Para modelos computarizados previos
    """
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    payment_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("payments.id"), unique=True, nullable=True
    )
    invoice_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    control_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # ── Bolivia SIN ────────────────────────────────────────────
    cuf: Mapped[Optional[str]] = mapped_column(Text, nullable=True,
                                                comment="Código Único de Factura")
    cufd: Mapped[Optional[str]] = mapped_column(Text, nullable=True,
                                                 comment="Código Único de Facturación Diaria")

    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    pdf_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Relaciones ─────────────────────────────────────────────
    payment: Mapped[Optional["Payment"]] = relationship("Payment", back_populates="invoice")
