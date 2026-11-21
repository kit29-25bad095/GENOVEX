from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, EmailStr, ConfigDict
from app.core.security import RoleEnum

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: Optional[RoleEnum] = RoleEnum.PATIENT
    credentials_summary: Optional[str] = None

class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    credentials_summary: Optional[str] = None

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: str
    full_name: str
    role: RoleEnum
    credentials_summary: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: RoleEnum
    credentials_summary: Optional[str] = None
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    user_email: Optional[str] = None
    user_role: Optional[str] = None
    action: str
    resource_type: str
    resource_id: str
    details: Optional[Any] = None
    ip_address: Optional[str] = None
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)

class UserUpdateRequest(BaseModel):
    role: Optional[RoleEnum] = None
    credentials_summary: Optional[str] = None
    is_active: Optional[bool] = None
    full_name: Optional[str] = None

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ForgotPasswordResponse(BaseModel):
    status: str = "success"
    message: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
    confirm_password: Optional[str] = None

class ResetPasswordResponse(BaseModel):
    status: str = "success"
    message: str
