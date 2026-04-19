"""Paquete crud."""
from app.crud.user import crud_user
from app.crud.workshop import crud_workshop
from app.crud.incident import crud_incident

__all__ = ["crud_user", "crud_workshop", "crud_incident"]
