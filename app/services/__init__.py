"""
Paquete services — lógica de negocio e integraciones externas.

Módulos disponibles:
  - ai_service: Análisis de imágenes con IA (requiere: boto3, httpx)
  - qr_service: Pagos QR interoperables Bolivia (requiere: qrcode)
  - geo_service: Utilidades geoespaciales (requiere: shapely, geopy)

Importa directamente el módulo que necesites:
  from app.services.geo_service import geo_service
"""
