from pydantic import BaseModel
from typing import Optional

class UserSchema(BaseModel):
    id: Optional[int] = None
    name: str
    email: str
    password: str
    phone: Optional[str]
    location: Optional[str]