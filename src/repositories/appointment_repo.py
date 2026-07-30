from typing import List, Dict, Any, Optional
from datetime import datetime, date
from bson import ObjectId
from src.repositories.base import BaseRepository
from src.enums import AppointmentStatus


class AppointmentRepository(BaseRepository):
    def __init__(self):
        super().__init__("appointments")

    async def create_appointment(self, time_slot_id: str, barber_id: str, client_id: str,
                               client_phone: str, client_name: str,
                               appointment_date: date, appointment_time) -> str:
        """Create a new appointment"""
        # Convert date to datetime (MongoDB requires datetime, not date)
        date_dt = datetime.combine(appointment_date, datetime.min.time())

        # Convert time to string if needed
        time_str = appointment_time.strftime("%H:%M") if hasattr(appointment_time, 'strftime') else str(appointment_time)

        appointment_data = {
            "time_slot_id": ObjectId(time_slot_id),
            "barber_id": ObjectId(barber_id),
            "client_id": ObjectId(client_id),
            "client_phone": client_phone,
            "client_name": client_name,
            "status": AppointmentStatus.BOOKED.value,
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
        """Find all appointments for a client"""
        return await self.find_many({"client_id": ObjectId(client_id)})

    async def find_by_barber(self, barber_id: str) -> List[Dict[str, Any]]:
        """Find all appointments for a barber"""
        return await self.find_many({"barber_id": ObjectId(barber_id)})

    async def find_by_barber_and_date(self, barber_id: str, date_obj: date) -> List[Dict[str, Any]]:
        """Find appointments for a barber on a specific date"""
        # Convert date to datetime range
        date_start = datetime.combine(date_obj, datetime.min.time())
        date_end = datetime.combine(date_obj, datetime.max.time())

        return await self.find_many({
            "barber_id": ObjectId(barber_id),
            "appointment_date": {"$gte": date_start, "$lte": date_end}
        })

    async def find_by_time_slot(self, time_slot_id: str) -> Optional[Dict[str, Any]]:
        """Find appointment by time slot ID"""
        return await self.find_one({"time_slot_id": ObjectId(time_slot_id)})

    async def find_reminders_needed(self, date_obj: date) -> List[Dict[str, Any]]:
        """Find appointments that need reminders sent"""
        # Convert date to datetime range
        date_start = datetime.combine(date_obj, datetime.min.time())
        date_end = datetime.combine(date_obj, datetime.max.time())

        return await self.find_many({
            "appointment_date": {"$gte": date_start, "$lte": date_end},
            "reminder_sent": False,
            "status": AppointmentStatus.BOOKED.value
        })

    async def cancel_appointment(self, appointment_id: str, cancelled_by: str, reason: str) -> bool:
        """Cancel an appointment"""
        return await self.update(appointment_id, {
            "status": AppointmentStatus.CANCELLED.value,
            "cancelled_by": cancelled_by,
            "cancelled_at": datetime.utcnow(),
            "cancel_reason": reason,
            "updated_at": datetime.utcnow()
        })

    async def mark_reminder_sent(self, appointment_id: str) -> bool:
        """Mark reminder as sent"""
        return await self.update(appointment_id, {
            "reminder_sent": True,
            "reminder_sent_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })

    async def find_active(self, client_id: str) -> List[Dict[str, Any]]:
        """Find active (booked) appointments for a client"""
        return await self.find_many({
            "client_id": ObjectId(client_id),
            "status": AppointmentStatus.BOOKED.value
        })

    async def find_by_barber_active(self, barber_id: str) -> List[Dict[str, Any]]:
        """Find active appointments for a barber"""
        return await self.find_many({
            "barber_id": ObjectId(barber_id),
            "status": AppointmentStatus.BOOKED.value
        })
