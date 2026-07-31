from datetime import datetime, date, time, timedelta
from typing import List, Dict, Any
from bson import ObjectId
from src.repositories import ScheduleRepository, TimeSlotRepository
from src.utils import get_timezone, logger
import pytz


class ScheduleService:
    def __init__(self):
        self.schedule_repo = ScheduleRepository()
        self.time_slot_repo = TimeSlotRepository()

    async def create_schedule(
        self,
        barber_id: str,
        date_obj: date,
        start_time: time,
        end_time: time,
        haircut_duration_minutes: int = 60,
        haircut_and_beard_duration_minutes: int = 90,
    ) -> Dict[str, Any]:
        """
        Create a new schedule (slots generated on-the-fly during booking).

        Args:
            barber_id: Barber's ID
            date_obj: Date of the schedule
            start_time: Start time of work
            end_time: End time of work
            haircut_duration_minutes: Duration for haircut service
            haircut_and_beard_duration_minutes: Duration for haircut+beard service

        Returns:
            Created schedule
        """
        schedule_id = await self.schedule_repo.create_schedule(
            barber_id,
            date_obj,
            start_time,
            end_time,
            haircut_duration_minutes,
            haircut_and_beard_duration_minutes,
        )
        logger.info(
            f"Created schedule {schedule_id} for barber {barber_id} on {date_obj}"
        )

        schedule = await self.schedule_repo.find_by_id(schedule_id)
        return schedule

    async def _generate_time_slots(
        self,
        schedule_id: str,
        barber_id: str,
        date_obj: date,
        start_time: time,
        end_time: time,
        duration_minutes: int,
    ) -> int:
        """Generate time slots for a schedule"""
        tz = get_timezone()
        current_time = datetime.combine(date_obj, start_time)
        current_time = tz.localize(current_time)
        end_datetime = datetime.combine(date_obj, end_time)
        end_datetime = tz.localize(end_datetime)

        slots_created = 0
        while current_time < end_datetime:
            slot_end = current_time + timedelta(minutes=duration_minutes)

            # Only skip if slot_end exceeds end_datetime (allow equal end time)
            if slot_end > end_datetime:
                break

            logger.info(f"Creating slot: {current_time} - {slot_end}")
            await self.time_slot_repo.create_slot(
                schedule_id, barber_id, current_time, slot_end
            )
            slots_created += 1
            current_time = slot_end

        logger.info(f"Total slots created: {slots_created}")
        return slots_created

    async def publish_schedule(self, schedule_id: str) -> bool:
        """Mark schedule as published"""
        result = await self.schedule_repo.publish_schedule(schedule_id)
        if result:
            logger.info(f"Published schedule {schedule_id}")
        return result

    async def get_barber_schedules(self, barber_id: str) -> List[Dict[str, Any]]:
        """Get all schedules for a barber"""
        return await self.schedule_repo.find_by_barber(barber_id)

    async def get_available_slots_for_service(
        self, barber_id: str, date_obj: date, service_type: str = "haircut"
    ) -> List[Dict[str, Any]]:
        """Get available time slots for a specific service type and date"""
        # Find schedule for barber on this date
        schedule = await self.schedule_repo.find_by_barber_and_date(barber_id, date_obj)
        if not schedule:
            return []

        # Get service duration
        duration_key = (
            "haircut_and_beard_duration_minutes"
            if service_type == "haircut_and_beard"
            else "haircut_duration_minutes"
        )
        duration = schedule.get(duration_key, 60)

        # Generate available slots
        slots = await self._generate_available_slots(
            schedule,
            duration,
            service_type,
        )
        return slots

    async def _generate_available_slots(
        self, schedule: Dict[str, Any], duration_minutes: int, service_type: str
    ) -> List[Dict[str, Any]]:
        """Generate available slots for a service based on schedule"""
        tz = get_timezone()

        # Parse start and end times from schedule
        date_obj = (
            schedule["date"].date()
            if hasattr(schedule["date"], "date")
            else schedule["date"]
        )
        start_time = schedule["start_time"]
        end_time = schedule["end_time"]

        # Parse time strings if needed
        if isinstance(start_time, str):
            start_hour, start_min = map(int, start_time.split(":"))
            start_time = time(hour=start_hour, minute=start_min)
        if isinstance(end_time, str):
            end_hour, end_min = map(int, end_time.split(":"))
            end_time = time(hour=end_hour, minute=end_min)

        # Create datetime objects
        current_time = datetime.combine(date_obj, start_time)
        current_time = tz.localize(current_time)
        end_datetime = datetime.combine(date_obj, end_time)
        end_datetime = tz.localize(end_datetime)

        slots = []
        while current_time < end_datetime:
            slot_end = current_time + timedelta(minutes=duration_minutes)

            if slot_end > end_datetime:
                break

            slot = {
                "_id": str(schedule["_id"]),  # Use schedule ID as reference
                "start_time": current_time,
                "end_time": slot_end,
                "barber_id": schedule["barber_id"],
                "service_type": service_type,
                "status": "available",
            }
            slots.append(slot)
            current_time = slot_end

        return slots

    async def get_available_slots_for_barber(
        self, barber_id: str, date_obj: date
    ) -> List[Dict[str, Any]]:
        """Get available time slots for a barber on a specific date (for barber view)"""
        return await self.time_slot_repo.find_available_for_date(barber_id, date_obj)

    async def cancel_schedule(self, schedule_id: str, reason: str) -> bool:
        """Cancel a schedule and all related appointments"""
        # Delete time slots (they will be cascade deleted with appointments)
        await self.time_slot_repo.delete_by_schedule(schedule_id)

        # Delete schedule
        result = await self.schedule_repo.delete(schedule_id)
        logger.info(f"Cancelled schedule {schedule_id}. Reason: {reason}")
        return result
