from datetime import date, datetime, time

import pytz

from src.config import settings


def get_timezone():
    """Get timezone object from settings"""
    return pytz.timezone(settings.timezone)


def get_now():
    """Get current datetime in configured timezone"""
    tz = get_timezone()
    return datetime.now(tz)


def get_today():
    """Get today's date in configured timezone"""
    return get_now().date()


def combine_datetime(date_obj: date, time_obj: time) -> datetime:
    """Combine date and time objects into aware datetime"""
    dt = datetime.combine(date_obj, time_obj)
    tz = get_timezone()
    return tz.localize(dt)


def is_time_in_past(dt: datetime) -> bool:
    """Check if datetime is in the past"""
    return dt < get_now()


def get_date_at_time(target_date: date, target_time: time) -> datetime:
    """Get aware datetime for a specific date and time"""
    return combine_datetime(target_date, target_time)
