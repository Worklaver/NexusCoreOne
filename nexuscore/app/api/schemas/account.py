from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class AccountStatus(str, Enum):
    ACTIVE = "active"
    COOLING_DOWN = "cooling_down"
    BANNED = "banned"
    NEEDS_VERIFICATION = "needs_verification"
    LIMITED = "limited"
    INACTIVE = "inactive"

class AccountBase(BaseModel):
    phone: str = Field(..., description="Account phone number")
    api_id: str = Field(..., description="Telegram API ID")
    api_hash: str = Field(..., description="Telegram API hash")
    
class AccountCreate(AccountBase):
    user_id: int = Field(..., description="User ID who owns this account")
    
class AccountUpdate(BaseModel):
    phone: Optional[str] = Field(None, description="Account phone number")
    api_id: Optional[str] = Field(None, description="Telegram API ID")
    api_hash: Optional[str] = Field(None, description="Telegram API hash")
    is_active: Optional[bool] = Field(None, description="Is account active")
    status: Optional[str] = Field(None, description="Account status")

class AccountResponse(BaseModel):
    id: int
    user_id: int
    phone: str
    api_id: str
    api_hash: str  # This will be masked in the API response
    is_active: bool
    status: str
    last_used: Optional[datetime] = None
    cooldown_until: Optional[datetime] = None
    daily_parse_count: int
    daily_invite_count: int
    daily_like_count: int
    reset_counts_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True

class AccountHealthResponse(BaseModel):
    account_id: int
    status: str
    is_connected: bool
    is_authorized: bool
    has_restrictions: bool
    details: Optional[str] = None