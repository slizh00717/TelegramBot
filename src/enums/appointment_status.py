from enum import StrEnum


class AppointmentStatus(StrEnum):
    BOOKED = "booked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
