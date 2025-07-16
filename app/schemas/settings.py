from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class SettingsCreate(BaseModel):
    credential_name: str = Field(..., min_length=1, max_length=100)
    username: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1)


class SettingsUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=1, max_length=255)
    password: Optional[str] = Field(None, min_length=1)
    is_active: Optional[bool] = None


class SettingsResponse(BaseModel):
    credential_name: str
    username: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_login_attempt: Optional[datetime] = None
    login_success_count: int
    login_failure_count: int

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    credential_name: str = Field(..., min_length=1, max_length=100)


# Backward compatibility aliases
CredentialCreate = SettingsCreate
CredentialUpdate = SettingsUpdate
CredentialResponse = SettingsResponse
