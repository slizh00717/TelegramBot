from datetime import datetime

from bson import ObjectId
from pydantic import BaseModel, Field

from src.enums import NotificationType
from src.models.base import PyObjectId


class NotificationCreate(BaseModel):
    recipient_id: str
    type: NotificationType
    title: str
    message: str
    related_appointment_id: str | None = None
    related_schedule_id: str | None = None


class NotificationRead(BaseModel):
    id: PyObjectId = Field(default_factory=ObjectId, alias="_id")
    recipient_id: PyObjectId
    type: NotificationType
    title: str
    message: str
    related_appointment_id: PyObjectId | None = None
    related_schedule_id: PyObjectId | None = None
    is_sent: bool = False
    sent_at: datetime | None = None
    sent_method: str | None = None
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
    error_message: str | None = None
