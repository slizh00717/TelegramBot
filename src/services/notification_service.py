from typing import Optional, Dict, Any, List
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from src.repositories import NotificationRepository, UserRepository
from src.enums import NotificationType
from src.config import settings
from src.utils import logger


class NotificationService:
    def __init__(self, bot: Optional[Bot] = None):
        self.notification_repo = NotificationRepository()
        self.user_repo = UserRepository()
        self.bot = bot

    async def send_message(
        self,
        chat_id: int,
        message_text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
    ) -> bool:
        """Send a message via Telegram"""
        if not self.bot:
            logger.warning("Bot not initialized, cannot send message")
            return False

        try:
            await self.bot.send_message(
                chat_id, message_text, parse_mode="HTML", reply_markup=reply_markup
            )
            logger.info(f"Sent message to {chat_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to send message to {chat_id}: {e}")
            return False

    async def create_notification(
        self,
        recipient_id: str,
        notification_type: NotificationType,
        title: str,
        message: str,
        related_appointment_id: Optional[str] = None,
        related_schedule_id: Optional[str] = None,
    ) -> str:
        """Create a notification record"""
        notification_id = await self.notification_repo.create_notification(
            recipient_id=recipient_id,
            notification_type=notification_type,
            title=title,
            message=message,
            related_appointment_id=related_appointment_id,
            related_schedule_id=related_schedule_id,
        )
        return notification_id

    async def notify_user(
        self,
        user_id: str,
        notification_type: NotificationType,
        title: str,
        message: str,
        related_appointment_id: Optional[str] = None,
        related_schedule_id: Optional[str] = None,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
    ) -> bool:
        """Create notification and send it to user"""
        # Get user
        user = await self.user_repo.find_by_id(user_id)
        if not user:
            logger.warning(f"User {user_id} not found")
            return False

        # Check if user is blocked
        if user.get("is_blocked", False):
            logger.info(f"User {user_id} is blocked, skipping notification")
            return False

        # Create notification record
        notification_id = await self.create_notification(
            recipient_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            related_appointment_id=related_appointment_id,
            related_schedule_id=related_schedule_id,
        )

        # Send message
        if await self.send_message(
            user["telegram_id"], message, reply_markup=reply_markup
        ):
            # Mark as sent
            await self.notification_repo.mark_sent(notification_id, "TELEGRAM")
            return True

        return False

    async def notify_subscribers(
        self,
        notification_type: NotificationType,
        title: str,
        message: str,
        exclude_user_id: Optional[str] = None,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        batch_size: int = 100,
    ) -> int:
        """Send notification to all subscribed clients.

        Uses batch processing to avoid loading all users into memory at once.

        Args:
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            exclude_user_id: User ID to exclude from notification
            reply_markup: Optional keyboard markup
            batch_size: Number of users to process at once (default: 100)

        Returns:
            Number of successfully sent notifications
        """
        sent_count = 0
        skip = 0

        while True:
            # Load users in batches to avoid memory overload
            clients = await self.user_repo.find_many(
                {"is_subscribed": True, "is_blocked": False},
                limit=batch_size,
                skip=skip,
            )

            if not clients:
                break

            for client in clients:
                if exclude_user_id and str(client["_id"]) == exclude_user_id:
                    continue

                success = await self.notify_user(
                    user_id=str(client["_id"]),
                    notification_type=notification_type,
                    title=title,
                    message=message,
                    reply_markup=reply_markup,
                )

                if success:
                    sent_count += 1

            skip += batch_size

        logger.info(f"Sent '{title}' notification to {sent_count} subscribers")
        return sent_count

    async def send_schedule_published_notification(
        self, schedule_id: str, barber_name: str, date_str: str, available_slots: int
    ) -> int:
        """Send schedule published notification to all subscribers"""
        message = (
            f"<b>✂️ Новое расписание от {barber_name}</b>\n\n"
            f"📅 Дата: {date_str}\n"
            f"🕐 Доступно мест: {available_slots}\n\n"
            f"Запишись прямо сейчас!"
        )

        return await self.notify_subscribers(
            notification_type=NotificationType.SCHEDULE_PUBLISHED,
            title="Расписание опубликовано",
            message=message,
        )

    async def send_appointment_booked_notification(
        self, barber_id: str, client_name: str, appointment_time: str
    ) -> bool:
        """Send notification to barber about new appointment"""
        barber = await self.user_repo.find_by_id(barber_id)
        if not barber:
            return False

        message = (
            f"<b>📅 Новая запись</b>\n\n"
            f"👤 Клиент: {client_name}\n"
            f"🕐 Время: {appointment_time}"
        )

        return await self.notify_user(
            user_id=barber_id,
            notification_type=NotificationType.APPOINTMENT_BOOKED,
            title="Новая запись",
            message=message,
        )

    async def send_appointment_cancelled_notification(
        self, client_id: str, reason: str
    ) -> bool:
        """Send notification to client about cancelled appointment"""
        message = (
            f"<b>❌ Ваша запись была отменена</b>\n\n"
            f"Причина: {reason}\n\n"
            f"Вы можете записаться на другое время"
        )

        return await self.notify_user(
            user_id=client_id,
            notification_type=NotificationType.APPOINTMENT_CANCELLED,
            title="Запись отменена",
            message=message,
        )

    async def send_reminder_notification(
        self,
        client_id: str,
        appointment_time: str,
        appointment_date: Optional[str] = None,
        barber_address: Optional[str] = None,
    ) -> bool:
        """Send reminder notification to client"""
        message = "<b>⏰ Напоминание о вашей записи</b>\n\n"

        if appointment_date:
            message += f"📅 Дата: {appointment_date}\n"

        message += f"🕐 Время: {appointment_time}\n"

        if barber_address:
            message += f"📍 Адрес: {barber_address}\n"

        message += f"\nДо встречи! ✂️"

        return await self.notify_user(
            user_id=client_id,
            notification_type=NotificationType.REMINDER,
            title="Напоминание о записи",
            message=message,
        )

    async def send_slot_available_notification(
        self, barber_id: str, slot_time: str
    ) -> bool:
        """Send notification to barber about available slot"""
        message = (
            f"<b>✨ Место освободилось</b>\n\n"
            f"🕐 Время: {slot_time}\n\n"
            f"Вы можете сообщить своим клиентам об этом месте"
        )

        return await self.notify_user(
            user_id=barber_id,
            notification_type=NotificationType.SLOT_AVAILABLE,
            title="Место освободилось",
            message=message,
        )

    def set_bot(self, bot: Bot):
        """Set bot instance for sending messages"""
        self.bot = bot
