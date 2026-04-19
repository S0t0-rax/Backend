"""
Schemas de Autenticación — JWT tokens.
"""
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPayload(BaseModel):
    sub: str        # user_id
    roles: list[str]
    type: str       # "access" | "refresh"
    exp: int
    iat: int


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
