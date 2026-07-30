import asyncio
import logging
from aiogram import Dispatcher, Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from src.config import settings
from src.database import MongoDB, create_indexes
from src.handlers import user_router, barber_router, client_router
from src.services import NotificationService
from src.tasks import BotScheduler
from src.utils import logger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def main():
    """Main entry point for the bot"""
    logger.info("Starting Barber Bot...")

    # Initialize database
    db = MongoDB.connect()
    create_indexes(db)
    logger.info("Database initialized")

    # Initialize bot with new aiogram 3.7+ syntax
    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # Set bot instance for notifications
    notification_service = NotificationService(bot)

    # Start scheduler for reminders
    await BotScheduler.start(notification_service)

    # Register routers
    dp.include_router(user_router)
    dp.include_router(barber_router)
    dp.include_router(client_router)

    logger.info("Bot started and listening for messages...")

    try:
        await dp.start_polling(bot)
    finally:
        BotScheduler.stop()
        await bot.session.close()
        MongoDB.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
