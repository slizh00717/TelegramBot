from datetime import datetime

from bson import ObjectId
from pydantic import BaseModel, Field

from src.enums import UserRole
from src.models.base import PyObjectId


class UserBase(BaseModel):
    telegram_id: int
    full_name: str
    phone: str | None = None
    address: str | None = None
    role: UserRole
    is_active: bool = True
    is_subscribed: bool = True
    is_blocked: bool = False


class UserCreate(UserBase):
    username: str | None = None


class UserUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    address: str | None = None
    is_subscribed: bool | None = None


class UserBarberUpdate(BaseModel):
    barber_name: str | None = None
    address: str | None = None
    description: str | None = None


class BarberService(BaseModel):
    haircut: float | None = None
    beard_trim: float | None = None
    haircut_and_beard: float | None = None
    updated_at: datetime | None = None


class ServiceHistory(BaseModel):
    haircut: float | None = None
    beard_trim: float | None = None
    haircut_and_beard: float | None = None
    updated_at: datetime


class UserRead(UserBase):
    id: PyObjectId = Field(default_factory=ObjectId, alias="_id")
    username: str | None = None
    visit_count: int = 0
    services: BarberService | None = None
    services_history: list | None = None
    referral_code: str | None = None
    referred_by: str | None = None
    referral_count: int = 0
    bonus_balance: float = 0
    reminder_time: str = "09:00"
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
