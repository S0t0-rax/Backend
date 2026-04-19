"""
QR Service — Generación y verificación de pagos QR interoperables (Bolivia).

Estándar: QR interoperable boliviano (Entidades financieras reguladas por BCB)
Flujo:
1. Se crea una orden de pago → se genera un QR
2. El cliente escanea el QR desde cualquier app bancaria
3. La pasarela notifica el pago via webhook → se confirma
"""
import io
import uuid
from typing import Any, Dict, Optional

import httpx
import qrcode
from loguru import logger
from qrcode.image.pil import PilImage

from app.core.config import settings


class QRPaymentService:
    """
    Servicio de pagos QR interoperable para Bolivia.
    Integrable con cualquier pasarela que soporte el estándar BCB.
    """

    def __init__(self):
        self._client = httpx.AsyncClient(timeout=15.0)

    async def create_payment_qr(
        self,
        service_order_id: int,
        amount: float,
        currency: str = "BOB",
        description: str = "Servicio mecánico",
    ) -> Dict[str, Any]:
        """
        Crea una solicitud de pago en la pasarela y genera el QR.

        Returns:
            {
                "transaction_id": "txn_abc123",
                "qr_code_image": "https://...",  # URL del QR en S3 o base64
                "qr_data": "00020101...",          # Payload EMV QR
                "expires_at": "2025-..."
            }
        """
        if not settings.QR_GATEWAY_URL:
            logger.warning("QR_GATEWAY_URL no configurado — generando QR mock")
            return await self._generate_mock_qr(service_order_id, amount, currency)

        try:
            response = await self._client.post(
                f"{settings.QR_GATEWAY_URL}/payments",
                headers={"Authorization": f"Bearer {settings.QR_GATEWAY_API_KEY}"},
                json={
                    "merchant_id": settings.QR_MERCHANT_ID,
                    "order_id": str(service_order_id),
                    "amount": str(amount),
                    "currency": currency,
                    "description": description,
                },
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error creando pago QR: {e}")
            raise

    async def verify_payment(self, transaction_id: str) -> Dict[str, Any]:
        """
        Consulta el estado de un pago en la pasarela.

        Returns:
            {"status": "completed" | "pending" | "failed", "paid_at": "..."}
        """
        if not settings.QR_GATEWAY_URL:
            return {"status": "completed", "mock": True}

        response = await self._client.get(
            f"{settings.QR_GATEWAY_URL}/payments/{transaction_id}",
            headers={"Authorization": f"Bearer {settings.QR_GATEWAY_API_KEY}"},
        )
        response.raise_for_status()
        return response.json()

    async def _generate_mock_qr(
        self, order_id: int, amount: float, currency: str
    ) -> Dict[str, Any]:
        """
        Genera un QR local para desarrollo/testing (sin pasarela real).
        El QR contiene los datos de pago en formato texto plano.
        """
        txn_id = f"MOCK-TXN-{uuid.uuid4().hex[:12].upper()}"
        qr_data = f"AAA_SERV|{order_id}|{amount}|{currency}|{txn_id}"

        # Generar imagen QR en memoria
        qr = qrcode.QRCode(version=1, box_size=8, border=4)
        qr.add_data(qr_data)
        qr.make(fit=True)
        img: PilImage = qr.make_image(fill_color="black", back_color="white")

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        # En producción esto se sube a S3; en dev retornamos el path mock
        logger.info(f"QR mock generado para orden {order_id}: {txn_id}")
        return {
            "transaction_id": txn_id,
            "qr_code_image": f"mock://qr/{txn_id}.png",
            "qr_data": qr_data,
            "mock": True,
        }

    async def close(self):
        await self._client.aclose()


qr_service = QRPaymentService()
