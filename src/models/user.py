from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict
from bson import ObjectId
from src.enums import UserRole
from src.models.base import PyObjectId


class UserBase(BaseModel):
    telegram_id: int
    full_name: str
    phone: Optional[str] = None
    address: Optional[str] = None
    role: UserRole
    is_active: bool = True
    is_subscribed: bool = True
    is_blocked: bool = False


class UserCreate(UserBase):
    username: Optional[str] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    is_subscribed: Optional[bool] = None


class UserBarberUpdate(BaseModel):
    barber_name: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None


class BarberService(BaseModel):
    haircut: Optional[float] = None
    beard_trim: Optional[float] = None
    haircut_and_beard: Optional[float] = None
    updated_at: Optional[datetime] = None


class ServiceHistory(BaseModel):
    haircut: Optional[float] = None
    beard_trim: Optional[float] = None
    haircut_and_beard: Optional[float] = None
    updated_at: datetime


class UserRead(UserBase):
    id: PyObjectId = Field(default_factory=ObjectId, alias="_id")
    username: Optional[str] = None
    visit_count: int = 0
    services: Optional[BarberService] = None
    services_history: Optional[list] = None
    referral_code: Optional[str] = None
    referred_by: Optional[str] = None
    referral_count: int = 0
    bonus_balance: float = 0
    reminder_time: str = "09:00"
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
