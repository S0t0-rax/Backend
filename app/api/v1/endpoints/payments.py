"""
Endpoints de Pagos QR — /api/v1/payments
"""
from fastapi import APIRouter

from app.api.dependencies import AnyStaff, CurrentUser, DBSession
from app.core.exceptions import NotFoundException
from app.crud.base import CRUDBase
from app.models.payment import Payment, PaymentMethod
from app.schemas.service_order import PaymentCreate, PaymentResponse
from app.services.qr_service import qr_service

router = APIRouter(prefix="/payments", tags=["💳 Pagos QR"])

_crud_payment = CRUDBase(Payment)
_crud_method = CRUDBase(PaymentMethod)


@router.post("/", response_model=PaymentResponse, status_code=201)
async def create_payment(data: PaymentCreate, _: AnyStaff, db: DBSession):
    """
    Inicia un pago QR para una orden de servicio.

    Flujo:
    1. Crea el registro de pago en BD (estado: pending)
    2. Solicita el QR a la pasarela de pago
    3. Retorna la URL del QR para mostrarlo al cliente
    """
    # Generar QR con la pasarela
    qr_result = await qr_service.create_payment_qr(
        service_order_id=data.service_order_id,
        amount=float(data.amount),
        currency=data.currency,
    )

    payment = Payment(
        service_order_id=data.service_order_id,
        payment_method_id=data.payment_method_id,
        amount=data.amount,
        currency=data.currency,
        transaction_id=qr_result.get("transaction_id"),
        qr_code_image=qr_result.get("qr_code_image"),
        payment_status="pending",
    )
    db.add(payment)
    await db.flush()
    await db.refresh(payment)
    return payment


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(payment_id: int, current_user: CurrentUser, db: DBSession):
    """Detalle de un pago."""
    payment = await _crud_payment.get(db, payment_id)
    if not payment:
        raise NotFoundException("Pago")
    return payment


@router.post("/{payment_id}/verify", response_model=PaymentResponse)
async def verify_payment(payment_id: int, _: AnyStaff, db: DBSession):
    """
    Consulta el estado del pago en la pasarela y actualiza en BD.
    Útil para polling o confirmación manual.
    """
    from datetime import datetime, timezone

    payment = await _crud_payment.get(db, payment_id)
    if not payment:
        raise NotFoundException("Pago")

    if payment.transaction_id:
        result = await qr_service.verify_payment(payment.transaction_id)
        if result.get("status") == "completed" and payment.payment_status != "completed":
            payment.payment_status = "completed"
            payment.paid_at = datetime.now(timezone.utc)
            db.add(payment)
            await db.flush()
            await db.refresh(payment)

    return payment
