"""
Schemas de Incidente + IncidentPhoto — Pydantic v2.
"""
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class IncidentCreate(BaseModel):
    car_id: int
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    address_reference: Optional[str] = None
    description: Optional[str] = None


class IncidentUpdate(BaseModel):
    description: Optional[str] = None
    severity_level: Optional[str] = None
    status: Optional[str] = None
    address_reference: Optional[str] = None


class IncidentPhotoResponse(BaseModel):
    id: int
    storage_url: str
    ai_detected_issue: Optional[str]
    ai_confidence_score: Optional[float]
    ai_metadata: Optional[Dict[str, Any]]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IncidentResponse(BaseModel):
    id: int
    client_id: Optional[int]
    car_id: Optional[int]
    address_reference: Optional[str]
    description: Optional[str]
    severity_level: str
    status: str
    reported_at: datetime
    photos: List[IncidentPhotoResponse] = []

    model_config = ConfigDict(from_attributes=True)


class IncidentGlobalResponse(IncidentResponse):
    """Schema extendido para el admin con info de quien atiende."""
    mechanic_name: Optional[str] = None
    workshop_name: Optional[str] = None
    client_name: Optional[str] = None
    # Podríamos añadir más campos de ServiceOrder si fuera necesario

