from datetime import datetime
from typing import Any

from bson import ObjectId

from src.enums import NotificationType
from src.repositories.base import BaseRepository


class NotificationRepository(BaseRepository):
    def __init__(self):
        super().__init__("notifications")

    async def create_notification(
        self,
        recipient_id: str,
        notification_type: NotificationType,
        title: str,
        message: str,
        related_appointment_id: str | None = None,
        related_schedule_id: str | None = None,
    ) -> str:
        """Create a new notification"""
        notification_data = {
            "recipient_id": ObjectId(recipient_id),
            "type": notification_type.value,
            "title": title,
            "message": message,
            "related_appointment_id": (ObjectId(related_appointment_id) if related_appointment_id else None),
            "related_schedule_id": (ObjectId(related_schedule_id) if related_schedule_id else None),
            "is_sent": False,
            "sent_at": None,
            "sent_method": None,
            "created_at": datetime.utcnow(),
        }
        return await self.create(notification_data)

    async def find_by_recipient(self, recipient_id: str) -> list[dict[str, Any]]:
        """Find all notifications for a recipient"""
        return await self.find_many({"recipient_id": ObjectId(recipient_id)})

    async def find_unsent(self) -> list[dict[str, Any]]:
        """Find all unsent notifications"""
        return await self.find_many({"is_sent": False})

    async def find_by_type(self, notification_type: NotificationType) -> list[dict[str, Any]]:
        """Find notifications by type"""
        return await self.find_many({"type": notification_type.value})

    async def mark_sent(self, notification_id: str, sent_method: str = "TELEGRAM") -> bool:
        """Mark notification as sent"""
        return await self.update(
            notification_id,
            {"is_sent": True, "sent_at": datetime.utcnow(), "sent_method": sent_method},
        )

    async def find_by_appointment(self, appointment_id: str) -> list[dict[str, Any]]:
        """Find notifications related to an appointment"""
        return await self.find_many({"related_appointment_id": ObjectId(appointment_id)})
