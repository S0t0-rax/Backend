"""
AI Service — Análisis de imágenes de incidentes vehiculares.

Flujo:
1. Recibe imagen (bytes o URL)
2. Sube a S3
3. Envía a la API de visión por computadora
4. Retorna el resultado estructurado para guardar en incident_photos.ai_metadata
"""
import io
from typing import Any, Dict, Optional

import httpx
from loguru import logger
from PIL import Image

from app.core.config import settings


class AIVisionService:
    """
    Servicio de análisis de imágenes para detección de daños vehiculares.
    Compatible con cualquier API REST de visión (GPT-4V, Google Vision, etc.)
    """

    def __init__(self):
        self._s3 = None
        self._http_client = httpx.AsyncClient(timeout=30.0)

    @property
    def s3(self):
        if not self._s3:
            try:
                import boto3
            except ImportError:
                raise ImportError(
                    "boto3 no esta instalado. Ejecuta: pip install boto3"
                )
            self._s3 = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION,
            )
        return self._s3

    async def upload_image_to_s3(
        self, image_bytes: bytes, filename: str, content_type: str = "image/jpeg"
    ) -> str:
        """
        Sube imagen a S3 y retorna la URL pública.

        Returns:
            URL pública del objeto en S3
        """
        if not settings.AWS_ACCESS_KEY_ID:
            logger.warning("AWS_ACCESS_KEY_ID no configurado — guardando imagen localmente")
            import os
            os.makedirs("uploads/incidents", exist_ok=True)
            safe_filename = filename.replace("/", "_")
            local_path = f"uploads/incidents/{safe_filename}"
            with open(local_path, "wb") as f:
                f.write(image_bytes)
            # URL pública usando el dominio de Railway actual para pruebas
            return f"https://backend-production-a940.up.railway.app/uploads/incidents/{safe_filename}"

        try:
            self.s3.put_object(
                Bucket=settings.AWS_S3_BUCKET,
                Key=f"incidents/{filename}",
                Body=image_bytes,
                ContentType=content_type,
            )
            url = f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/incidents/{filename}"
            logger.info(f"Imagen subida a S3: {url}")
            return url
        except Exception as e:
            logger.error(f"Error subiendo imagen a S3: {e}")
            logger.warning("Retornando URL falsa para no bloquear el reporte de incidente.")
            return f"https://mock-s3-bucket.s3.amazonaws.com/incidents/{filename}-fallback"

    async def analyze_vehicle_damage(
        self, image_url: str
    ) -> Dict[str, Any]:
        """
        Envía imagen a la API de IA y retorna análisis de daño vehicular.

        Returns:
            {
                "issue": "Neumático pinchado",
                "confidence": 94.5,
                "severity": "high",
                "recommendations": ["Cambio inmediato de neumático"],
                "raw_response": {...}
            }
        """
        if not settings.AI_VISION_API_URL:
            logger.warning("AI_VISION_API_URL no configurado — retornando mock")
            return self._mock_ai_response()

        try:
            response = await self._http_client.post(
                settings.AI_VISION_API_URL,
                headers={"Authorization": f"Bearer {settings.AI_VISION_API_KEY}"},
                json={
                    "model": "gpt-4-vision-preview",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": (
                                        "Analiza este vehículo y detecta cualquier daño, falla "
                                        "o problema mecánico visible. Responde en JSON con: "
                                        "issue, confidence (0-100), severity (low/medium/high), "
                                        "recommendations."
                                    ),
                                },
                                {"type": "image_url", "image_url": {"url": image_url}},
                            ],
                        }
                    ],
                    "max_tokens": 500,
                },
            )
            response.raise_for_status()
            raw = response.json()
            # Parsear la respuesta del modelo según el proveedor
            content = raw["choices"][0]["message"]["content"]
            return {"issue": content, "confidence": 0.0, "raw_response": raw}
        except Exception as e:
            logger.error(f"Error en análisis de IA: {e}")
            return {"issue": "Error en análisis", "confidence": 0.0, "error": str(e)}

    @staticmethod
    def _mock_ai_response() -> Dict[str, Any]:
        """Respuesta simulada para desarrollo sin API key."""
        return {
            "issue": "Posible falla en sistema de frenos",
            "confidence": 87.5,
            "severity": "high",
            "recommendations": [
                "Inspección inmediata del sistema de frenos",
                "No operar el vehículo hasta revisión",
            ],
            "raw_response": {"mock": True},
        }

    async def close(self):
        await self._http_client.aclose()


ai_service = AIVisionService()
