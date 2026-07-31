from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from src.services import ReminderService, NotificationService
from src.utils import logger, get_timezone
import pytz


class BotScheduler:
    _instance = None
    _scheduler = None

    @classmethod
    def get_scheduler(cls) -> AsyncIOScheduler:
        """Get or create scheduler instance (singleton)"""
        if cls._scheduler is None:
            cls._scheduler = AsyncIOScheduler()
        return cls._scheduler

    @classmethod
    async def start(cls, notification_service: NotificationService):
        """Start the scheduler with all jobs"""
        scheduler = cls.get_scheduler()

        if scheduler.running:
            logger.warning("Scheduler is already running")
            return

        # Schedule reminder checks for each hour (00:00 to 23:00)
        tz = get_timezone()
        for hour in range(24):
            scheduler.add_job(
                send_hourly_reminders,
                CronTrigger(hour=hour, minute=0, timezone=tz),
                id=f"hourly_reminders_{hour:02d}",
                name=f"Send reminders at {hour:02d}:00",
                replace_existing=True,
                args=[notification_service, hour],
            )

        scheduler.start()
        logger.info("Scheduler started with 24 hourly reminder jobs")

    @classmethod
    def stop(cls):
        """Stop the scheduler"""
        if cls._scheduler and cls._scheduler.running:
            cls._scheduler.shutdown()
            logger.info("Scheduler stopped")

    @classmethod
    def is_running(cls) -> bool:
        """Check if scheduler is running"""
        return cls._scheduler is not None and cls._scheduler.running


async def send_hourly_reminders(notification_service: NotificationService, hour: int):
    """Job that sends reminders for a specific hour"""
    try:
        from src.utils import get_today
        from src.repositories import AppointmentRepository, UserRepository

        hour_str = f"{hour:02d}:00"

        # Get all appointments for today that need reminders
        today = get_today()
        appointment_repo = AppointmentRepository()
        user_repo = UserRepository()

        appointments = await appointment_repo.find_reminders_needed(today)
        sent_count = 0

        for appt in appointments:
            # Get client's reminder time preference
            client = await user_repo.find_by_id(str(appt["client_id"]))
            if not client:
                continue

            client_reminder_time = client.get("reminder_time", "09:00")

            # Only send if this is the client's preferred reminder time
            if client_reminder_time == hour_str:
                success = await notification_service.send_reminder_notification(
                    client_id=str(appt["client_id"]),
                    appointment_time=str(appt["appointment_time"]),
                )

                if success:
                    await appointment_repo.mark_reminder_sent(str(appt["_id"]))
                    sent_count += 1

        if sent_count > 0:
            logger.info(
                f"Hourly reminders job ({hour_str}): sent {sent_count} reminders"
            )

    except Exception as e:
        logger.error(f"Error in hourly reminders job (hour={hour}): {e}", exc_info=True)
