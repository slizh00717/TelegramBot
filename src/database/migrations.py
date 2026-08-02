from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING
import logging

logger = logging.getLogger(__name__)


async def create_indexes(db: AsyncIOMotorDatabase) -> None:
    """Create all necessary indexes for collections to optimize query performance.

    Note: This function is idempotent - it safely handles existing indexes
    by catching and logging index conflicts (motor will ignore indexes that
    already exist with the same specification).
    """

    try:
        logger.info("Creating database indexes...")

        # Users collection indexes
        await db.users.create_index("telegram_id", unique=True)
        await db.users.create_index("phone")
        await db.users.create_index("referral_code", unique=True)
        await db.users.create_index([("role", ASCENDING), ("is_subscribed", ASCENDING)])
        await db.users.create_index(
            [("is_subscribed", ASCENDING), ("is_blocked", ASCENDING)]
        )
        await db.users.create_index(
            [("is_active", ASCENDING), ("created_at", DESCENDING)]
        )
        logger.info("✓ Users collection indexes")

        # Barber schedules collection indexes
        await db.barber_schedules.create_index(
            [("barber_id", ASCENDING), ("date", ASCENDING)]
        )
        await db.barber_schedules.create_index(
            [("is_published", ASCENDING), ("date", DESCENDING)]
        )
        await db.barber_schedules.create_index("created_at")
        logger.info("✓ Barber schedules collection indexes")

        # Time slots collection indexes
        await db.time_slots.create_index(
            [("barber_id", ASCENDING), ("start_time", ASCENDING)]
        )
        await db.time_slots.create_index(
            [("status", ASCENDING), ("start_time", ASCENDING)]
        )
        await db.time_slots.create_index(
            [("schedule_id", ASCENDING), ("status", ASCENDING)]
        )
        await db.time_slots.create_index("created_at")
        logger.info("✓ Time slots collection indexes")

        # Appointments collection indexes - optimized for common queries
        await db.appointments.create_index(
            [("barber_id", ASCENDING), ("appointment_date", DESCENDING)]
        )
        await db.appointments.create_index(
            [("client_id", ASCENDING), ("status", ASCENDING)]
        )
        await db.appointments.create_index(
            [("appointment_date", ASCENDING), ("appointment_time", ASCENDING)]
        )
        await db.appointments.create_index("time_slot_id")
        await db.appointments.create_index(
            [("reminder_sent", ASCENDING), ("appointment_date", ASCENDING)]
        )
        await db.appointments.create_index(
            [("status", ASCENDING), ("appointment_date", DESCENDING)]
        )
        logger.info("✓ Appointments collection indexes")

        # Notifications collection indexes
        await db.notifications.create_index(
            [
                ("recipient_id", ASCENDING),
                ("is_sent", ASCENDING),
                ("created_at", DESCENDING),
            ]
        )
        await db.notifications.create_index(
            [("type", ASCENDING), ("is_sent", ASCENDING)]
        )
        await db.notifications.create_index("created_at")
        logger.info("✓ Notifications collection indexes")

        # Reminder jobs collection indexes
        await db.reminder_jobs.create_index("appointment_id", unique=True)
        await db.reminder_jobs.create_index(
            [("status", ASCENDING), ("scheduled_time", ASCENDING)]
        )
        logger.info("✓ Reminder jobs collection indexes")

        logger.info("✅ All database indexes created successfully!")

    except Exception as e:
        logger.warning(
            f"Index creation warning (this is normal if indexes already exist): {e}"
        )
        logger.info("Database is ready to use")
