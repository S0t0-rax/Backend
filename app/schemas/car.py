"""
Schemas para Vehículos (Cars) — Pydantic v2.
"""
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class CarBase(BaseModel):
    license_plate: str = Field(..., min_length=5, max_length=20)
    model: str = Field(..., min_length=2, max_length=100)
    brand: str = Field(..., min_length=2, max_length=50)
    year: Optional[int] = Field(None, ge=1900, le=2100)
    color: Optional[str] = Field(None, max_length=30)


class CarCreate(CarBase):
    pass


class CarUpdate(BaseModel):
    model: Optional[str] = None
    brand: Optional[str] = None
    year: Optional[int] = None
    color: Optional[str] = None


class CarResponse(CarBase):
    id: int
    owner_id: int

    model_config = ConfigDict(from_attributes=True)
