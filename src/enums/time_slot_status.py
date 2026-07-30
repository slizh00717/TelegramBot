from enum import Enum


class TimeSlotStatus(str, Enum):
    AVAILABLE = "available"
    BOOKED = "booked"
    LOCKED = "locked"
