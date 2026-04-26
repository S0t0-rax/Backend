"""
Schemas de Usuario — Pydantic v2.
"""
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserLocationUpdate(BaseModel):
    """Actualiza la ubicación GPS del usuario (lat, lng)."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    role_name: Optional[str] = Field("client", description="Rol deseado para la cuenta")


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    phone: Optional[str]
    is_active: bool
    status: str = "available"
    current_incident_id: Optional[int] = None
    roles: List[str] = []

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_with_roles(cls, user) -> "UserResponse":
        return cls(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            phone=user.phone,
            is_active=user.is_active,
            status=getattr(user, 'status', 'available'),
            current_incident_id=getattr(user, 'current_incident_id', None),
            roles=[r.name for r in user.roles],
        )


class MechanicStaffResponse(UserResponse):
    """Respuesta para el endpoint de gestión de personal del dueño.

    Incluye si el mecánico está ocupado y el taller donde está trabajando actualmente.
    """
    workshop_id: Optional[int] = None
    workshop_name: Optional[str] = None
    active_tasks_count: int = 0
    active_incident_ids: List[int] = []

class AdminUserUpdate(BaseModel):
    """Schema para edición de usuarios desde el panel Admin"""
    is_active: Optional[bool] = None
    role_name: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
