"""
Schemas de Car — Pydantic v2.
"""
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class CarCreate(BaseModel):
    license_plate: str = Field(..., min_length=3, max_length=20)
    model: str = Field(..., max_length=100)
    brand: str = Field(..., max_length=50)
    year: Optional[int] = Field(None, ge=1900, le=2100)
    color: Optional[str] = Field(None, max_length=30)


class CarUpdate(BaseModel):
    model: Optional[str] = None
    brand: Optional[str] = None
    year: Optional[int] = Field(None, ge=1900, le=2100)
    color: Optional[str] = None


class CarResponse(BaseModel):
    id: int
    owner_id: int
    license_plate: str
    model: str
    brand: str
    year: Optional[int]
    color: Optional[str]

    model_config = ConfigDict(from_attributes=True)
