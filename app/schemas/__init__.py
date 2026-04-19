"""Paquete schemas."""
from app.schemas.auth import LoginRequest, TokenResponse, RefreshRequest, TokenPayload
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserLocationUpdate
from app.schemas.car import CarCreate, CarUpdate, CarResponse
from app.schemas.incident import IncidentCreate, IncidentUpdate, IncidentResponse, IncidentPhotoResponse
from app.schemas.workshop import WorkshopCreate, WorkshopUpdate, WorkshopResponse, NearbyWorkshopResponse
from app.schemas.service_order import ServiceOrderCreate, ServiceOrderUpdate, ServiceOrderResponse, PaymentCreate, PaymentResponse, InvoiceResponse

__all__ = [
    "LoginRequest", "TokenResponse", "RefreshRequest", "TokenPayload",
    "UserCreate", "UserUpdate", "UserResponse", "UserLocationUpdate",
    "CarCreate", "CarUpdate", "CarResponse",
    "IncidentCreate", "IncidentUpdate", "IncidentResponse", "IncidentPhotoResponse",
    "WorkshopCreate", "WorkshopUpdate", "WorkshopResponse", "NearbyWorkshopResponse",
    "ServiceOrderCreate", "ServiceOrderUpdate", "ServiceOrderResponse",
    "PaymentCreate", "PaymentResponse", "InvoiceResponse",
]
