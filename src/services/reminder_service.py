from datetime import datetime, time, timedelta
from typing import Optional, List, Dict, Any
from src.repositories import AppointmentRepository
from src.services.notification_service import NotificationService
from src.utils import logger, get_timezone, get_date_at_time


class ReminderService:
    def __init__(self, notification_service: NotificationService):
        self.appointment_repo = AppointmentRepository()
        self.notification_service = notification_service

    async def send_reminder_for_appointment(self, appointment_id: str) -> bool:
        """Send reminder notification for an appointment"""
        appointment = await self.appointment_repo.find_by_id(appointment_id)
        if not appointment:
            logger.warning(f"Appointment {appointment_id} not found")
            return False

        # Format appointment time
        appointment_time = appointment["appointment_time"]
        if isinstance(appointment_time, time):
            time_str = appointment_time.strftime("%H:%M")
        else:
            time_str = str(appointment_time)

        # Send reminder
        success = await self.notification_service.send_reminder_notification(
            client_id=str(appointment["client_id"]), appointment_time=time_str
        )

        if success:
            # Mark reminder as sent
            await self.appointment_repo.mark_reminder_sent(appointment_id)
            logger.info(f"Sent reminder for appointment {appointment_id}")

        return success

    async def send_daily_reminders(self) -> int:
        """Send reminders for all appointments today"""
        from src.utils import get_today

        today = get_today()

        # Find appointments that need reminders
        appointments = await self.appointment_repo.find_reminders_needed(today)
        logger.info(
            f"Found {len(appointments)} appointments that need reminders for today"
        )

        sent_count = 0
        for appointment in appointments:
            success = await self.send_reminder_for_appointment(str(appointment["_id"]))
            if success:
                sent_count += 1

        logger.info(
            f"Sent {sent_count} reminders out of {len(appointments)} appointments"
        )
        return sent_count

    async def schedule_reminders_for_date(self, target_date) -> List[Dict[str, Any]]:
        """
        Schedule reminders for a specific date.
        This is called by APScheduler.

        Returns:
            List of scheduled appointment IDs
        """
        logger.info(f"Scheduling reminders for {target_date}")
        # This will be called by APScheduler at 09:00 each day
        return []
