from enum import StrEnum


class TimeSlotStatus(StrEnum):
    AVAILABLE = "available"
    BOOKED = "booked"
    LOCKED = "locked"
