from pymongo.database import Database
from pymongo import ASCENDING, DESCENDING
import logging

logger = logging.getLogger(__name__)


def create_indexes(db: Database) -> None:
    """Create all necessary indexes for collections"""

    # Users collection
    db.users.create_index("telegram_id", unique=True, sparse=True)
    db.users.create_index("role")
    db.users.create_index("is_subscribed")
    logger.info("Created indexes for users collection")

    # Barber schedules collection
    db.barber_schedules.create_index([("barber_id", ASCENDING), ("date", ASCENDING)])
    db.barber_schedules.create_index("is_published")
    logger.info("Created indexes for barber_schedules collection")

    # Time slots collection
    db.time_slots.create_index([("barber_id", ASCENDING), ("start_time", ASCENDING)])
    db.time_slots.create_index([("status", ASCENDING), ("start_time", ASCENDING)])
    db.time_slots.create_index("schedule_id")
    logger.info("Created indexes for time_slots collection")

    # Appointments collection
    db.appointments.create_index(
        [("barber_id", ASCENDING), ("appointment_date", DESCENDING)]
    )
    db.appointments.create_index([("client_id", ASCENDING), ("status", ASCENDING)])
    db.appointments.create_index(
        [("appointment_date", ASCENDING), ("appointment_time", ASCENDING)]
    )
    db.appointments.create_index(
        "time_slot_id"
    )  # Not unique - allows multiple bookings on same slot if cancelled
    db.appointments.create_index("reminder_sent")
    logger.info("Created indexes for appointments collection")

    # Notifications collection
    db.notifications.create_index([("recipient_id", ASCENDING), ("is_sent", ASCENDING)])
    db.notifications.create_index("type")
    logger.info("Created indexes for notifications collection")

    # Reminder jobs collection
    db.reminder_jobs.create_index("appointment_id", unique=True)
    db.reminder_jobs.create_index(
        [("status", ASCENDING), ("scheduled_time", ASCENDING)]
    )
    logger.info("Created indexes for reminder_jobs collection")
