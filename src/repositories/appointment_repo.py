from typing import List, Dict, Any, Optional, Union
from datetime import datetime, date, time
from bson import ObjectId
from src.repositories.base import BaseRepository
from src.enums import AppointmentStatus


class AppointmentRepository(BaseRepository):
    """Repository for appointment collection operations.

    Manages all database operations for appointments including creation, retrieval,
    cancellation, and reminder tracking.
    """

    def __init__(self) -> None:
        """Initialize AppointmentRepository with appointments collection."""
        super().__init__("appointments")

    @staticmethod
    def _format_time_to_string(appointment_time: Union[time, str]) -> str:
        """Convert time object or string to HH:MM format.

        Args:
            appointment_time: Time as datetime.time object or string

        Returns:
            Time formatted as HH:MM string

        Raises:
            ValueError: If appointment_time is not time or str type
        """
        if isinstance(appointment_time, time):
            return appointment_time.strftime("%H:%M")
        elif isinstance(appointment_time, str):
            return appointment_time
        else:
            raise ValueError(
                f"Invalid time type: {type(appointment_time)}. Expected time or str."
            )

    async def create_appointment(
        self,
        time_slot_id: str,
        barber_id: str,
        client_id: str,
        client_phone: str,
        client_name: str,
        appointment_date: date,
        appointment_time: Union[time, str],
        service_type: str = "haircut",
    ) -> str:
        """Create a new appointment.

        Args:
            time_slot_id: ID of the time slot
            barber_id: ID of the barber
            client_id: ID of the client
            client_phone: Client's phone number
            client_name: Client's name
            appointment_date: Date of appointment
            appointment_time: Time of appointment (time object or HH:MM string)
            service_type: Type of service (default: haircut)

        Returns:
            String ID of created appointment
        """
        # Convert date to datetime (MongoDB requires datetime, not date)
        date_dt = datetime.combine(appointment_date, datetime.min.time())

        # Convert time to string if needed
        time_str = self._format_time_to_string(appointment_time)

        appointment_data = {
            "time_slot_id": ObjectId(time_slot_id),
            "barber_id": ObjectId(barber_id),
            "client_id": ObjectId(client_id),
            "client_phone": client_phone,
            "client_name": client_name,
            "status": AppointmentStatus.BOOKED.value,
            "service_type": service_type,
            "cancelled_by": None,
            "cancelled_at": None,
            "cancel_reason": None,
            "appointment_date": date_dt,
            "appointment_time": time_str,
            "notes": None,
            "reminder_sent": False,
            "reminder_sent_at": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        return await self.create(appointment_data)

    async def find_by_client(self, client_id: str) -> List[Dict[str, Any]]:
        """Find all appointments for a client.

        Args:
            client_id: Client's user ID

        Returns:
            List of appointment documents for the client
        """
        return await self.find_many({"client_id": ObjectId(client_id)})

    async def find_by_barber(self, barber_id: str) -> List[Dict[str, Any]]:
        """Find all appointments for a barber.

        Args:
            barber_id: Barber's user ID

        Returns:
            List of appointment documents for the barber
        """
        return await self.find_many({"barber_id": ObjectId(barber_id)})

    async def find_by_barber_and_date(
        self, barber_id: str, date_obj: date
    ) -> List[Dict[str, Any]]:
        """Find appointments for a barber on a specific date.

        Args:
            barber_id: Barber's user ID
            date_obj: Date to query

        Returns:
            List of appointment documents for that barber on that date
        """
        # Convert date to datetime range
        date_start = datetime.combine(date_obj, datetime.min.time())
        date_end = datetime.combine(date_obj, datetime.max.time())

        return await self.find_many(
            {
                "barber_id": ObjectId(barber_id),
                "appointment_date": {"$gte": date_start, "$lte": date_end},
            }
        )

    async def find_by_time_slot(self, time_slot_id: str) -> Optional[Dict[str, Any]]:
        """Find appointment by time slot ID.

        Args:
            time_slot_id: Time slot ID to search for

        Returns:
            Appointment document or None if not found
        """
        return await self.find_one({"time_slot_id": ObjectId(time_slot_id)})

    async def find_reminders_needed(self, date_obj: date) -> List[Dict[str, Any]]:
        """Find appointments that need reminders sent for a specific date.

        Args:
            date_obj: Date to query for reminders

        Returns:
            List of booked appointments without sent reminders
        """
        # Convert date to datetime range
        date_start = datetime.combine(date_obj, datetime.min.time())
        date_end = datetime.combine(date_obj, datetime.max.time())

        return await self.find_many(
            {
                "appointment_date": {"$gte": date_start, "$lte": date_end},
                "reminder_sent": False,
                "status": AppointmentStatus.BOOKED.value,
            }
        )

    async def cancel_appointment(
        self, appointment_id: str, cancelled_by: str, reason: str
    ) -> bool:
        """Cancel an appointment with reason tracking.

        Args:
            appointment_id: ID of appointment to cancel
            cancelled_by: Who cancelled ("CLIENT" or "BARBER")
            reason: Reason for cancellation

        Returns:
            True if appointment was cancelled, False if not found
        """
        return await self.update(
            appointment_id,
            {
                "status": AppointmentStatus.CANCELLED.value,
                "cancelled_by": cancelled_by,
                "cancelled_at": datetime.utcnow(),
                "cancel_reason": reason,
                "updated_at": datetime.utcnow(),
            },
        )

    async def mark_reminder_sent(self, appointment_id: str) -> bool:
        """Mark reminder notification as sent.

        Args:
            appointment_id: ID of appointment to update

        Returns:
            True if reminder was marked sent, False if not found
        """
        return await self.update(
            appointment_id,
            {
                "reminder_sent": True,
                "reminder_sent_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
        )

    async def find_active(self, client_id: str) -> List[Dict[str, Any]]:
        """Find all active (booked) appointments for a client.

        Args:
            client_id: Client's user ID

        Returns:
            List of booked appointments for the client
        """
        return await self.find_many(
            {"client_id": ObjectId(client_id), "status": AppointmentStatus.BOOKED.value}
        )

    async def find_by_barber_active(self, barber_id: str) -> List[Dict[str, Any]]:
        """Find all active appointments for a barber.

        Args:
            barber_id: Barber's user ID

        Returns:
            List of booked appointments for the barber
        """
        return await self.find_many(
            {"barber_id": ObjectId(barber_id), "status": AppointmentStatus.BOOKED.value}
        )
