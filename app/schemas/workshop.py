"""
Schemas de Workshop — Pydantic v2.
"""
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class WorkshopCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    tax_id: Optional[str] = Field(None, max_length=50)
    address_text: str = Field(..., min_length=5)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class WorkshopUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=150)
    address_text: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)


class WorkshopResponse(BaseModel):
    id: int
    owner_id: Optional[int]
    name: str
    tax_id: Optional[str]
    address_text: str
    rating: Optional[Decimal]

    model_config = ConfigDict(from_attributes=True)


class NearbyWorkshopResponse(WorkshopResponse):
    """Taller con distancia calculada (búsqueda por proximidad)."""
    distance_meters: float
