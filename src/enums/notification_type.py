from enum import Enum


class NotificationType(str, Enum):
    SCHEDULE_PUBLISHED = "schedule_published"
    APPOINTMENT_BOOKED = "appointment_booked"
    APPOINTMENT_CANCELLED = "appointment_cancelled"
    REMINDER = "reminder"
    SLOT_AVAILABLE = "slot_available"
