from datetime import date, datetime
from typing import List, Dict, Any, Optional
from bson import ObjectId
import pytz
from src.repositories import AppointmentRepository, TimeSlotRepository, UserRepository
from src.enums import AppointmentStatus
from src.utils import logger, get_timezone
from src.config import settings


class AppointmentService:
    def __init__(self):
        self.appointment_repo = AppointmentRepository()
        self.time_slot_repo = TimeSlotRepository()
        self.user_repo = UserRepository()

    async def book_appointment(
        self, slot, client_id: str, service_type: str = "haircut"
    ) -> Optional[Dict[str, Any]]:
        """
        Book an appointment for a client on a time slot.

        Args:
            slot: Either a slot ID (string) or a slot object (dict)
            client_id: ID of the client
            service_type: Type of service ("haircut" or "haircut_and_beard")

        Returns:
            Created appointment or None if booking failed
        """
        # Handle both old (ID-based) and new (object-based) slot formats
        if isinstance(slot, str):
            # Old format: get from database
            time_slot = await self.time_slot_repo.find_by_id_typed(slot)
            if not time_slot:
                logger.warning(f"Time slot {slot} not found")
                return None
            time_slot_id = slot
        else:
            # New format: slot is already a dict with slot info
            time_slot = slot
            time_slot_id = str(time_slot.get("_id", ""))

        # Get client data
        client = await self.user_repo.find_by_id(client_id)
        if not client:
            logger.warning(f"Client {client_id} not found")
            return None

        # Convert UTC datetime from MongoDB back to local timezone
        tz = get_timezone()
        start_time_utc = time_slot["start_time"]

        logger.info(
            f"Original start_time from slot: {start_time_utc}, tzinfo: {start_time_utc.tzinfo}"
        )

        # If datetime is timezone-naive (from MongoDB), assume it's UTC
        if start_time_utc.tzinfo is None:
            start_time_utc = pytz.utc.localize(start_time_utc)

        logger.info(f"After UTC localize: {start_time_utc}")

        # Convert to local timezone
        start_time_local = start_time_utc.astimezone(tz)

        logger.info(f"After convert to local: {start_time_local}")
        logger.info(f"Local time only: {start_time_local.time()}")

        # Create appointment with service type
        appointment_id = await self.appointment_repo.create_appointment(
            time_slot_id=time_slot_id,
            barber_id=str(time_slot["barber_id"]),
            client_id=client_id,
            client_phone=client.get("phone", ""),
            client_name=client.get("full_name", ""),
            appointment_date=start_time_local.date(),
            appointment_time=start_time_local.time(),
            service_type=service_type,
        )

        # Book the time slot if it exists in DB
        if isinstance(slot, str):
            await self.time_slot_repo.book_slot(time_slot_id)

        logger.info(
            f"Booked appointment {appointment_id} for client {client_id}, service: {service_type}"
        )
        appointment = await self.appointment_repo.find_by_id(appointment_id)
        return appointment

    async def cancel_appointment(
        self, appointment_id: str, cancelled_by: str, reason: str
    ) -> bool:
        """
        Cancel an appointment and release the time slot.

        Args:
            appointment_id: ID of the appointment
            cancelled_by: "CLIENT" or "BARBER"
            reason: Reason for cancellation

        Returns:
            True if successful, False otherwise
        """
        # Get appointment
        appointment = await self.appointment_repo.find_by_id(appointment_id)
        if not appointment:
            logger.warning(f"Appointment {appointment_id} not found")
            return False

        # Cancel appointment
        result = await self.appointment_repo.cancel_appointment(
            appointment_id, cancelled_by, reason
        )

        if result:
            # Release time slot
            time_slot_id = str(appointment["time_slot_id"])
            await self.time_slot_repo.release_slot(time_slot_id)
            logger.info(
                f"Cancelled appointment {appointment_id}. Cancelled by: {cancelled_by}"
            )

        return result

    async def get_client_appointments(self, client_id: str) -> List[Dict[str, Any]]:
        """Get all appointments for a client"""
        return await self.appointment_repo.find_by_client(client_id)

    async def get_client_active_appointments(
        self, client_id: str
    ) -> List[Dict[str, Any]]:
        """Get active (booked) appointments for a client"""
        return await self.appointment_repo.find_active(client_id)

    async def get_barber_appointments(self, barber_id: str) -> List[Dict[str, Any]]:
        """Get all appointments for a barber"""
        return await self.appointment_repo.find_by_barber(barber_id)

    async def get_barber_appointments_for_date(
        self, barber_id: str, date_obj: date
    ) -> List[Dict[str, Any]]:
        """Get appointments for a barber on a specific date"""
        return await self.appointment_repo.find_by_barber_and_date(barber_id, date_obj)

    async def get_appointment_by_time_slot(
        self, time_slot_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get appointment by time slot ID"""
        return await self.appointment_repo.find_by_time_slot(time_slot_id)

    async def find_reminders_needed(self, date_obj: date) -> List[Dict[str, Any]]:
        """Find appointments that need reminders sent today"""
        return await self.appointment_repo.find_reminders_needed(date_obj)

    async def mark_reminder_sent(self, appointment_id: str) -> bool:
        """Mark reminder as sent for an appointment"""
        return await self.appointment_repo.mark_reminder_sent(appointment_id)

    async def complete_appointment(self, appointment_id: str) -> bool:
        """
        Mark appointment as completed and award referral bonus if applicable.

        Args:
            appointment_id: ID of the appointment

        Returns:
            True if successful, False otherwise
        """
        # Get appointment
        appointment = await self.appointment_repo.find_by_id(appointment_id)
        if not appointment:
            logger.warning(f"Appointment {appointment_id} not found")
            return False

        # Mark as completed
        result = await self.appointment_repo.update(
            appointment_id,
            {
                "status": AppointmentStatus.COMPLETED.value,
                "completed_at": datetime.utcnow(),
            },
        )

        if not result:
            return False

        # Check if client has a referrer (early exit if not)
        client_id = str(appointment["client_id"])
        client = await self.user_repo.find_by_id(client_id)

        if not client or not client.get("referred_by"):
            return True

        # Check if this is the first completed appointment (using count for efficiency)
        completed_count = await self.appointment_repo.collection.count_documents(
            {
                "client_id": ObjectId(client_id),
                "status": AppointmentStatus.COMPLETED.value,
            }
        )

        # Award bonus only for first completed appointment
        if completed_count == 1:
            referrer_id = client.get("referred_by")
            bonus_points = settings.referral_bonus_points
            success = await self.user_repo.add_bonus_balance(referrer_id, bonus_points)
            if success:
                logger.info(
                    f"Awarded {bonus_points} bonus points to {referrer_id} for first referral completion"
                )

        return True
