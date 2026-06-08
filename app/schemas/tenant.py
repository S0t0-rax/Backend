from pydantic import BaseModel, ConfigDict
from typing import Optional

class TenantBase(BaseModel):
    name: str
    tax_id: Optional[str] = None
    subdomain: Optional[str] = None

class TenantCreate(TenantBase):
    pass

class TenantUpdate(BaseModel):
    name: Optional[str] = None
    tax_id: Optional[str] = None
    subdomain: Optional[str] = None
    is_active: Optional[bool] = None

class TenantResponse(TenantBase):
    id: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

class TenantRegistrationRequest(BaseModel):
    """Payload para registrar un Tenant nuevo con su usuario administrador."""
    tenant_name: str
    tax_id: Optional[str] = None
    admin_full_name: str
    admin_email: str
    admin_password: str
