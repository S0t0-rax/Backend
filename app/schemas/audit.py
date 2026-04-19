"""
Schemas de Bitácora / Auditoría.
"""
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int]
    action: str
    entity: str
    entity_id: Optional[str]
    details: Optional[Dict[str, Any]]
    created_at: datetime
    ip_address: Optional[str]

    model_config = ConfigDict(from_attributes=True)
