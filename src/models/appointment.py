from pydantic import BaseModel, Field
from datetime import datetime, date, time
from typing import Optional, Literal
from bson import ObjectId
from src.enums import AppointmentStatus


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return v
        return ObjectId(v)


class AppointmentCreate(BaseModel):
    time_slot_id: str
    barber_id: str
    client_id: str
    client_phone: str
    client_name: str
    appointment_date: date
    appointment_time: time


class AppointmentUpdate(BaseModel):
    status: Optional[AppointmentStatus] = None
    notes: Optional[str] = None


class AppointmentCancel(BaseModel):
    cancelled_by: Literal["CLIENT", "BARBER"]
    cancel_reason: str


class AppointmentRead(BaseModel):
    id: PyObjectId = Field(default_factory=ObjectId, alias="_id")
    time_slot_id: PyObjectId
    barber_id: PyObjectId
    client_id: PyObjectId
    client_phone: str
    client_name: str
    status: AppointmentStatus
    cancelled_by: Optional[Literal["CLIENT", "BARBER"]] = None
    cancelled_at: Optional[datetime] = None
    cancel_reason: Optional[str] = None
    appointment_date: date
    appointment_time: time
    notes: Optional[str] = None
    reminder_sent: bool = False
    reminder_sent_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
