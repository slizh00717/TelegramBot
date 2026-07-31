from pymongo.database import Database
from pymongo import ASCENDING, DESCENDING
import logging

logger = logging.getLogger(__name__)


def create_indexes(db: Database) -> None:
    """Create all necessary indexes for collections to optimize query performance."""

    # Users collection indexes
    db.users.create_index("telegram_id", unique=True, sparse=True)
    db.users.create_index("phone", sparse=True)
    db.users.create_index("referral_code", unique=True, sparse=True)
    db.users.create_index([("role", ASCENDING), ("is_subscribed", ASCENDING)])
    db.users.create_index([("is_subscribed", ASCENDING), ("is_blocked", ASCENDING)])
    db.users.create_index([("is_active", ASCENDING), ("created_at", DESCENDING)])
    logger.info("✓ Created indexes for users collection (6 indexes)")

    # Barber schedules collection indexes
    db.barber_schedules.create_index(
        [("barber_id", ASCENDING), ("date", ASCENDING)], unique=True
    )
    db.barber_schedules.create_index([("is_published", ASCENDING), ("date", DESCENDING)])
    db.barber_schedules.create_index("created_at")
    logger.info("✓ Created indexes for barber_schedules collection (3 indexes)")

    # Time slots collection indexes
    db.time_slots.create_index([("barber_id", ASCENDING), ("start_time", ASCENDING)])
    db.time_slots.create_index([("status", ASCENDING), ("start_time", ASCENDING)])
    db.time_slots.create_index([("schedule_id", ASCENDING), ("status", ASCENDING)])
    db.time_slots.create_index("created_at")
    logger.info("✓ Created indexes for time_slots collection (4 indexes)")

    # Appointments collection indexes - optimized for common queries
    db.appointments.create_index(
        [("barber_id", ASCENDING), ("appointment_date", DESCENDING)]
    )
    db.appointments.create_index([("client_id", ASCENDING), ("status", ASCENDING)])
    db.appointments.create_index([("appointment_date", ASCENDING), ("appointment_time", ASCENDING)])
    db.appointments.create_index("time_slot_id")
    db.appointments.create_index([("reminder_sent", ASCENDING), ("appointment_date", ASCENDING)])
    db.appointments.create_index([("status", ASCENDING), ("appointment_date", DESCENDING)])
    logger.info("✓ Created indexes for appointments collection (6 indexes)")

    # Notifications collection indexes
    db.notifications.create_index(
        [("recipient_id", ASCENDING), ("is_sent", ASCENDING), ("created_at", DESCENDING)]
    )
    db.notifications.create_index([("type", ASCENDING), ("is_sent", ASCENDING)])
    db.notifications.create_index("created_at")
    logger.info("✓ Created indexes for notifications collection (3 indexes)")

    # Reminder jobs collection indexes
    db.reminder_jobs.create_index("appointment_id", unique=True, sparse=True)
    db.reminder_jobs.create_index([("status", ASCENDING), ("scheduled_time", ASCENDING)])
    logger.info("✓ Created indexes for reminder_jobs collection (2 indexes)")

    logger.info("All database indexes created successfully!")
