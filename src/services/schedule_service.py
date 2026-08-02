from datetime import date, datetime, time, timedelta
from typing import Any

from src.repositories import ScheduleRepository, TimeSlotRepository
from src.utils import get_timezone, logger


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
        beard_trim_duration_minutes: int = 30,
        haircut_and_beard_duration_minutes: int = 90,
    ) -> dict[str, Any]:
        """
        Create a new schedule (slots generated on-the-fly during booking).

        Args:
            barber_id: Barber's ID
            date_obj: Date of the schedule
            start_time: Start time of work
            end_time: End time of work
            haircut_duration_minutes: Duration for haircut service
            beard_trim_duration_minutes: Duration for beard trim service
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
            beard_trim_duration_minutes,
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

    async def get_barber_schedules(self, barber_id: str) -> list[dict[str, Any]]:
        """Get all schedules for a barber"""
        return await self.schedule_repo.find_by_barber(barber_id)

    async def get_available_slots_for_service(
        self, barber_id: str, date_obj: date, service_type: str = "haircut"
    ) -> list[dict[str, Any]]:
        """Get available time slots for a specific service type and date"""
        from src.repositories import AppointmentRepository

        # Find schedule for barber on this date
        schedule = await self.schedule_repo.find_by_barber_and_date(barber_id, date_obj)
        if not schedule:
            return []

        # Get service duration based on service type
        if service_type == "haircut_and_beard":
            duration_key = "haircut_and_beard_duration_minutes"
            default_duration = 90
        elif service_type == "beard_trim":
            duration_key = "beard_trim_duration_minutes"
            default_duration = 30
        else:  # haircut
            duration_key = "haircut_duration_minutes"
            default_duration = 60

        duration = schedule.get(duration_key, default_duration)

        # Get all booked appointments for this barber on this date
        appointment_repo = AppointmentRepository()
        booked_appointments = await appointment_repo.find_by_barber_and_date(
            barber_id, date_obj
        )

        # Get service durations for calculating appointment end times
        def get_duration_for_service(svc_type: str) -> int:
            """Get duration in minutes for a service type"""
            if svc_type == "haircut_and_beard":
                return schedule.get("haircut_and_beard_duration_minutes", 90)
            elif svc_type == "beard_trim":
                return schedule.get("beard_trim_duration_minutes", 30)
            else:  # haircut
                return schedule.get("haircut_duration_minutes", 60)

        # Create a sorted list of booked time ranges
        tz = get_timezone()
        booked_ranges = []
        for appt in booked_appointments:
            # Only consider BOOKED appointments, skip cancelled ones
            if appt.get("status") != "booked":
                continue

            appt_time_str = appt["appointment_time"]
            # Parse appointment time (format: "HH:MM")
            appt_hour, appt_min = map(int, appt_time_str.split(":"))
            appt_start = datetime.combine(
                date_obj, time(hour=appt_hour, minute=appt_min)
            )
            appt_start = tz.localize(appt_start)  # Make timezone-aware

            # Get service type and calculate duration
            svc_type = appt.get("service_type", "haircut")
            appt_duration = get_duration_for_service(svc_type)
            appt_end = appt_start + timedelta(minutes=appt_duration)

            booked_ranges.append((appt_start, appt_end))

        # Sort booked ranges by start time
        booked_ranges.sort(key=lambda x: x[0])

        # Parse schedule times
        start_time = schedule["start_time"]
        end_time = schedule["end_time"]

        if isinstance(start_time, str):
            start_hour, start_min = map(int, start_time.split(":"))
            start_time = time(hour=start_hour, minute=start_min)
        if isinstance(end_time, str):
            end_hour, end_min = map(int, end_time.split(":"))
            end_time = time(hour=end_hour, minute=end_min)

        # Create datetime objects for schedule
        work_start = datetime.combine(date_obj, start_time)
        work_start = tz.localize(work_start)
        work_end = datetime.combine(date_obj, end_time)
        work_end = tz.localize(work_end)

        # Generate slots in free windows between booked appointments
        available_slots = []

        if not booked_ranges:
            # No bookings - generate slots from work start to end
            current_time = work_start
            while current_time + timedelta(minutes=duration) <= work_end:
                slot = {
                    "_id": str(schedule["_id"]),
                    "start_time": current_time,
                    "end_time": current_time + timedelta(minutes=duration),
                    "barber_id": schedule["barber_id"],
                    "service_type": service_type,
                    "status": "available",
                }
                available_slots.append(slot)
                current_time = current_time + timedelta(minutes=duration)
        else:
            # Generate slots in gaps between bookings
            current_time = work_start

            for booked_start, booked_end in booked_ranges:
                # Generate slots in the gap before this booking
                while current_time + timedelta(minutes=duration) <= booked_start:
                    slot = {
                        "_id": str(schedule["_id"]),
                        "start_time": current_time,
                        "end_time": current_time + timedelta(minutes=duration),
                        "barber_id": schedule["barber_id"],
                        "service_type": service_type,
                        "status": "available",
                    }
                    available_slots.append(slot)
                    current_time = current_time + timedelta(minutes=duration)

                # Move past this booking
                current_time = booked_end

            # Generate slots after the last booking until work end
            while current_time + timedelta(minutes=duration) <= work_end:
                slot = {
                    "_id": str(schedule["_id"]),
                    "start_time": current_time,
                    "end_time": current_time + timedelta(minutes=duration),
                    "barber_id": schedule["barber_id"],
                    "service_type": service_type,
                    "status": "available",
                }
                available_slots.append(slot)
                current_time = current_time + timedelta(minutes=duration)

        return available_slots

    async def get_available_slots_for_barber(
        self, barber_id: str, date_obj: date
    ) -> list[dict[str, Any]]:
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
