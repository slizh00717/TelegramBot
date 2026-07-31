from typing import List, Dict, Any, Optional
from datetime import datetime
from bson import ObjectId
from src.repositories.base import BaseRepository
from src.enums import TimeSlotStatus


class TimeSlotRepository(BaseRepository):
    def __init__(self):
        super().__init__("time_slots")

    async def create_slot(
        self, schedule_id: str, barber_id: str, start_time: datetime, end_time: datetime
    ) -> str:
        """Create a new time slot"""
        slot_data = {
            "schedule_id": ObjectId(schedule_id),
            "barber_id": ObjectId(barber_id),
            "start_time": start_time,
            "end_time": end_time,
            "status": TimeSlotStatus.AVAILABLE.value,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        return await self.create(slot_data)

    async def find_by_schedule(self, schedule_id: str) -> List[Dict[str, Any]]:
        """Find all time slots for a schedule"""
        return await self.find_many({"schedule_id": ObjectId(schedule_id)})

    async def find_available_for_barber(self, barber_id: str) -> List[Dict[str, Any]]:
        """Find all available slots for a barber"""
        return await self.find_many(
            {"barber_id": ObjectId(barber_id), "status": TimeSlotStatus.AVAILABLE.value}
        )

    async def find_available_for_date(
        self, barber_id: str, date_obj
    ) -> List[Dict[str, Any]]:
        """Find available slots for a specific date"""
        from datetime import date as date_type

        if isinstance(date_obj, date_type):
            start_of_day = datetime.combine(date_obj, datetime.min.time())
            end_of_day = datetime.combine(date_obj, datetime.max.time())
        else:
            start_of_day = date_obj
            end_of_day = date_obj

        return await self.find_many(
            {
                "barber_id": ObjectId(barber_id),
                "status": TimeSlotStatus.AVAILABLE.value,
                "start_time": {"$gte": start_of_day, "$lte": end_of_day},
            }
        )

    async def book_slot(self, slot_id: str) -> bool:
        """Mark slot as booked"""
        return await self.update(
            slot_id,
            {"status": TimeSlotStatus.BOOKED.value, "updated_at": datetime.utcnow()},
        )

    async def release_slot(self, slot_id: str) -> bool:
        """Release a booked slot back to available"""
        return await self.update(
            slot_id,
            {"status": TimeSlotStatus.AVAILABLE.value, "updated_at": datetime.utcnow()},
        )

    async def find_by_id_typed(self, slot_id: str) -> Optional[Dict[str, Any]]:
        """Find slot by ID"""
        return await self.find_by_id(slot_id)

    async def delete_by_schedule(self, schedule_id: str) -> int:
        """Delete all slots for a schedule"""
        return await self.delete_many({"schedule_id": ObjectId(schedule_id)})
