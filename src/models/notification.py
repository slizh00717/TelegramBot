from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from bson import ObjectId
from src.enums import NotificationType


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return v
        return ObjectId(v)


class NotificationCreate(BaseModel):
    recipient_id: str
    type: NotificationType
    title: str
    message: str
    related_appointment_id: Optional[str] = None
    related_schedule_id: Optional[str] = None


class NotificationRead(BaseModel):
    id: PyObjectId = Field(default_factory=ObjectId, alias="_id")
    recipient_id: PyObjectId
    type: NotificationType
    title: str
    message: str
    related_appointment_id: Optional[PyObjectId] = None
    related_schedule_id: Optional[PyObjectId] = None
    is_sent: bool = False
    sent_at: Optional[datetime] = None
    sent_method: Optional[str] = None
    created_at: datetime

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}


class ReminderJobCreate(BaseModel):
    appointment_id: str
    scheduled_time: datetime
    job_id: str


class ReminderJobUpdate(BaseModel):
    status: str
    error_message: Optional[str] = None
