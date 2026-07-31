from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING
import logging

logger = logging.getLogger(__name__)


async def create_indexes(db: AsyncIOMotorDatabase) -> None:
    """Create all necessary indexes for collections to optimize query performance.

    Note: Uses create_index with default behavior - if index already exists with
    same key specification, it is silently ignored (idempotent).
    """

    # Users collection indexes
    await db.users.create_index("telegram_id", unique=True, sparse=True)
    await db.users.create_index("phone", sparse=True)
    await db.users.create_index("referral_code", unique=True, sparse=True)
    await db.users.create_index([("role", ASCENDING), ("is_subscribed", ASCENDING)])
    await db.users.create_index([("is_subscribed", ASCENDING), ("is_blocked", ASCENDING)])
    await db.users.create_index([("is_active", ASCENDING), ("created_at", DESCENDING)])
    logger.info("✓ Created indexes for users collection (6 indexes)")

    # Barber schedules collection indexes
    # Note: Not using unique=True because existing index was created without it
    # To make it unique, manually drop the index and recreate, or use database migration
    await db.barber_schedules.create_index(
        [("barber_id", ASCENDING), ("date", ASCENDING)]
    )
    await db.barber_schedules.create_index([("is_published", ASCENDING), ("date", DESCENDING)])
    await db.barber_schedules.create_index("created_at")
    logger.info("✓ Created indexes for barber_schedules collection (3 indexes)")

    # Time slots collection indexes
    await db.time_slots.create_index([("barber_id", ASCENDING), ("start_time", ASCENDING)])
    await db.time_slots.create_index([("status", ASCENDING), ("start_time", ASCENDING)])
    await db.time_slots.create_index([("schedule_id", ASCENDING), ("status", ASCENDING)])
    await db.time_slots.create_index("created_at")
    logger.info("✓ Created indexes for time_slots collection (4 indexes)")

    # Appointments collection indexes - optimized for common queries
    await db.appointments.create_index(
        [("barber_id", ASCENDING), ("appointment_date", DESCENDING)]
    )
    await db.appointments.create_index([("client_id", ASCENDING), ("status", ASCENDING)])
    await db.appointments.create_index([("appointment_date", ASCENDING), ("appointment_time", ASCENDING)])
    await db.appointments.create_index("time_slot_id")
    await db.appointments.create_index([("reminder_sent", ASCENDING), ("appointment_date", ASCENDING)])
    await db.appointments.create_index([("status", ASCENDING), ("appointment_date", DESCENDING)])
    logger.info("✓ Created indexes for appointments collection (6 indexes)")

    # Notifications collection indexes
    await db.notifications.create_index(
        [("recipient_id", ASCENDING), ("is_sent", ASCENDING), ("created_at", DESCENDING)]
    )
    await db.notifications.create_index([("type", ASCENDING), ("is_sent", ASCENDING)])
    await db.notifications.create_index("created_at")
    logger.info("✓ Created indexes for notifications collection (3 indexes)")

    # Reminder jobs collection indexes
    await db.reminder_jobs.create_index("appointment_id", unique=True, sparse=True)
    await db.reminder_jobs.create_index([("status", ASCENDING), ("scheduled_time", ASCENDING)])
    logger.info("✓ Created indexes for reminder_jobs collection (2 indexes)")

    logger.info("All database indexes created successfully!")
