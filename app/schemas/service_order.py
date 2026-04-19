"""
Schemas de ServiceOrder y Payment — Pydantic v2.
"""
from typing import Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


# ── Service Order ───────────────────────────────────────────────
class ServiceOrderCreate(BaseModel):
    incident_id: int
    mechanic_id: Optional[int] = None
    workshop_id: Optional[int] = None
    service_id: Optional[int] = None
    scheduled_at: Optional[datetime] = None
    estimated_cost: Optional[Decimal] = None


class ServiceOrderUpdate(BaseModel):
    mechanic_id: Optional[int] = None
    arrival_status: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    final_cost: Optional[Decimal] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)


class ServiceOrderResponse(BaseModel):
    id: int
    incident_id: Optional[int]
    mechanic_id: Optional[int]
    workshop_id: Optional[int]
    service_id: Optional[int]
    scheduled_at: Optional[datetime]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    estimated_cost: Optional[Decimal]
    final_cost: Optional[Decimal]
    arrival_status: Optional[str]

    model_config = ConfigDict(from_attributes=True)


# ── Payment ─────────────────────────────────────────────────────
class PaymentCreate(BaseModel):
    service_order_id: int
    payment_method_id: int
    amount: Decimal = Field(..., gt=0)
    currency: str = Field("BOB", max_length=3)


class PaymentResponse(BaseModel):
    id: int
    service_order_id: Optional[int]
    amount: Decimal
    currency: str
    payment_status: str
    transaction_id: Optional[str]
    qr_code_image: Optional[str]
    paid_at: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Invoice ─────────────────────────────────────────────────────
class InvoiceResponse(BaseModel):
    id: int
    payment_id: Optional[int]
    invoice_number: str
    cuf: Optional[str]
    cufd: Optional[str]
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    issued_at: datetime
    pdf_url: Optional[str]

    model_config = ConfigDict(from_attributes=True)
