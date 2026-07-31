from pydantic import BaseModel, Field
from datetime import datetime, date, time
from typing import Optional
from bson import ObjectId
from src.enums import TimeSlotStatus
from src.models.base import PyObjectId


class ScheduleCreate(BaseModel):
    barber_id: str
    date: date
    start_time: time
    end_time: time
    haircut_duration_minutes: int = 60
    beard_trim_duration_minutes: int = 30
    haircut_and_beard_duration_minutes: int = 90


class ScheduleUpdate(BaseModel):
    is_published: Optional[bool] = None


class ScheduleRead(BaseModel):
    id: PyObjectId = Field(default_factory=ObjectId, alias="_id")
    barber_id: PyObjectId
    date: date
    start_time: time
    end_time: time
    haircut_duration_minutes: int
    beard_trim_duration_minutes: int
    haircut_and_beard_duration_minutes: int
    is_published: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}


class TimeSlotCreate(BaseModel):
    schedule_id: str
    barber_id: str
    start_time: datetime
    end_time: datetime
    status: TimeSlotStatus = TimeSlotStatus.AVAILABLE


class TimeSlotRead(BaseModel):
    id: PyObjectId = Field(default_factory=ObjectId, alias="_id")
    schedule_id: PyObjectId
    barber_id: PyObjectId
    start_time: datetime
    end_time: datetime
    status: TimeSlotStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
