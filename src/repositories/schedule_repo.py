from datetime import date, datetime
from typing import Any

from bson import ObjectId

from src.repositories.base import BaseRepository


class ScheduleRepository(BaseRepository):
    def __init__(self):
        super().__init__("barber_schedules")

    async def create_schedule(
        self,
        barber_id: str,
        date_obj: date,
        start_time,
        end_time,
        haircut_duration_minutes: int = 60,
        beard_trim_duration_minutes: int = 30,
        haircut_and_beard_duration_minutes: int = 90,
    ) -> str:
        """Create a new schedule"""
        # Convert date to datetime (MongoDB requires datetime, not date)
        date_dt = datetime.combine(date_obj, datetime.min.time())

        # Convert time objects to strings (MongoDB can't encode datetime.time)
        start_time_str = (
            start_time.strftime("%H:%M")
            if hasattr(start_time, "strftime")
            else str(start_time)
        )
        end_time_str = (
            end_time.strftime("%H:%M")
            if hasattr(end_time, "strftime")
            else str(end_time)
        )

        schedule_data = {
            "barber_id": ObjectId(barber_id),
            "date": date_dt,
            "start_time": start_time_str,
            "end_time": end_time_str,
            "haircut_duration_minutes": haircut_duration_minutes,
            "beard_trim_duration_minutes": beard_trim_duration_minutes,
            "haircut_and_beard_duration_minutes": haircut_and_beard_duration_minutes,
            "is_published": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        return await self.create(schedule_data)

    async def find_by_barber_and_date(
        self, barber_id: str, date_obj: date
    ) -> dict[str, Any] | None:
        """Find schedule by barber and date"""
        # Convert date to datetime range query
        date_start = datetime.combine(date_obj, datetime.min.time())
        date_end = datetime.combine(date_obj, datetime.max.time())

        return await self.find_one(
            {
                "barber_id": ObjectId(barber_id),
                "date": {"$gte": date_start, "$lt": date_end},
            }
        )

    async def find_by_barber(
        self, barber_id: str, limit: int = 30
    ) -> list[dict[str, Any]]:
        """Find all schedules for a barber"""
        return await self.find_many({"barber_id": ObjectId(barber_id)}, limit=limit)

    async def find_unpublished(self) -> list[dict[str, Any]]:
        """Find all unpublished schedules"""
        return await self.find_many({"is_published": False})

    async def find_published(self) -> list[dict[str, Any]]:
        """Find all published schedules"""
        return await self.find_many({"is_published": True})

    async def publish_schedule(self, schedule_id: str) -> bool:
        """Mark schedule as published"""
        return await self.update(
            schedule_id, {"is_published": True, "updated_at": datetime.utcnow()}
        )

    async def find_schedules_after_date(
        self, barber_id: str, date_obj: date
    ) -> list[dict[str, Any]]:
        """Find schedules after a specific date for a barber"""
        # Convert date to datetime
        date_dt = datetime.combine(date_obj, datetime.min.time())

        return await self.find_many(
            {"barber_id": ObjectId(barber_id), "date": {"$gte": date_dt}}
        )
