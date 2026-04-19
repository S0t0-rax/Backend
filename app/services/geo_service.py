"""
Geo Service — Utilidades geoespaciales.

Funcionalidades:
- Geocodificación (dirección → coordenadas)
- Cálculo de distancias
- Conversión WKB ↔ lat/lng (PostGIS ↔ Python)
"""
from typing import Optional, Tuple

import shapely.wkb
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from loguru import logger
from shapely.geometry import Point


class GeoService:
    """Servicio de utilidades geoespaciales."""

    def __init__(self):
        self._geocoder = Nominatim(user_agent="aaa-serv-meca/1.0")

    def wkb_to_latlon(self, wkb_element) -> Optional[Tuple[float, float]]:
        """
        Convierte un elemento WKB de PostGIS/GeoAlchemy2 → (lat, lon).
        Útil para serializar coordenadas en respuestas JSON.

        Args:
            wkb_element: valor retornado por SQLAlchemy desde una columna Geography

        Returns:
            Tuple (latitude, longitude) o None si es nulo
        """
        if wkb_element is None:
            return None
        try:
            geom = shapely.wkb.loads(bytes(wkb_element.data), hex=False)
            # PostGIS: POINT(lon lat) → invertimos para (lat, lon)
            return (geom.y, geom.x)
        except Exception as e:
            logger.warning(f"Error convirtiendo WKB a lat/lon: {e}")
            return None

    def latlon_to_wkt(self, lat: float, lon: float) -> str:
        """
        Convierte lat/lon a formato WKT para PostGIS.
        PostGIS usa orden (lon lat) — no (lat lon).
        """
        return f"SRID=4326;POINT({lon} {lat})"

    def calculate_distance_km(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float,
    ) -> float:
        """
        Calcula la distancia geodésica entre dos puntos GPS.

        Returns:
            Distancia en kilómetros
        """
        return geodesic((lat1, lon1), (lat2, lon2)).kilometers

    async def geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Convierte una dirección de texto → (lat, lon).
        Usa Nominatim (OpenStreetMap) — para producción usar Google Maps API.
        """
        try:
            location = self._geocoder.geocode(address)
            if location:
                return (location.latitude, location.longitude)
        except Exception as e:
            logger.error(f"Error geocodificando '{address}': {e}")
        return None

    async def reverse_geocode(self, lat: float, lon: float) -> Optional[str]:
        """
        Convierte coordenadas → dirección de texto (reverse geocoding).
        """
        try:
            location = self._geocoder.reverse(f"{lat}, {lon}", language="es")
            if location:
                return location.address
        except Exception as e:
            logger.error(f"Error en reverse geocoding ({lat},{lon}): {e}")
        return None


geo_service = GeoService()
