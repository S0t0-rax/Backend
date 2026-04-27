import json
import os
import firebase_admin
from firebase_admin import credentials, messaging
from loguru import logger
from app.core.config import settings

class NotificationService:
    def __init__(self):
        self._initialized = False
        self._initialize_firebase()

    def _initialize_firebase(self):
        try:
            if not firebase_admin._apps:
                cert_data = settings.FIREBASE_SERVICE_ACCOUNT_JSON
                
                if not cert_data:
                    logger.warning("FIREBASE_SERVICE_ACCOUNT_JSON no está configurado. Las notificaciones no se enviarán.")
                    return

                # Si es un path de archivo
                if os.path.exists(cert_data):
                    cred = credentials.Certificate(cert_data)
                else:
                    # Si es el contenido JSON directamente
                    try:
                        cert_dict = json.loads(cert_data)
                        cred = credentials.Certificate(cert_dict)
                    except json.JSONDecodeError:
                        logger.error("FIREBASE_SERVICE_ACCOUNT_JSON no es un JSON válido ni un path existente.")
                        return

                firebase_admin.initialize_app(cred)
            
            self._initialized = True
            logger.info("Firebase Admin SDK inicializado correctamente.")
        except Exception as e:
            logger.error(f"Error al inicializar Firebase Admin SDK: {e}")

    async def send_push_notification(self, token: str, title: str, body: str, data: dict = None):
        """
        Envía una notificación push a un dispositivo específico.
        """
        if not self._initialized:
            logger.warning("Firebase no inicializado. No se puede enviar notificación.")
            return False

        if not token:
            logger.warning("Token de FCM vacío. Omitiendo notificación.")
            return False

        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=data or {},
                token=token,
            )
            response = messaging.send(message)
            logger.info(f"Notificación enviada exitosamente: {response}")
            return True
        except Exception as e:
            logger.error(f"Error al enviar notificación push: {e}")
            return False

    async def notify_status_change(self, user_token: str, status_type: str, details: dict = None):
        """
        Plantillas predefinidas para los estados solicitados por el usuario.
        """
        templates = {
            "request_accepted": {
                "title": "¡Solicitud Aceptada!",
                "body": "Un mecánico ha aceptado tu solicitud de servicio."
            },
            "mechanic_on_the_way": {
                "title": "Mecánico en camino",
                "body": f"El mecánico va hacia tu ubicación. Tiempo aprox: {details.get('eta', '15-30')} min." if details else "El mecánico va hacia tu ubicación."
            },
            "mechanic_arrived": {
                "title": "¡Mecánico ha llegado!",
                "body": "El mecánico se encuentra en el lugar de la solicitud."
            },
            "service_finished": {
                "title": "Reparación finalizada",
                "body": "Tu vehículo ha sido reparado con éxito. ¡Gracias por confiar en nosotros!"
            }
        }

        if status_type in templates:
            template = templates[status_type]
            return await self.send_push_notification(
                token=user_token,
                title=template["title"],
                body=template["body"],
                data=details
            )
        return False

notification_service = NotificationService()
