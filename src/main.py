import asyncio
import logging
import sys
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
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


async def main():
    """Main entry point for the bot"""
    logger.info("Starting Barber Bot...")

    # Initialize database
    try:
        db = MongoDB.connect()
        await create_indexes(db)
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}", exc_info=True)
        sys.exit(1)

    # Initialize bot with new aiogram 3.7+ syntax
    try:
        bot = Bot(
            token=settings.telegram_bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
    except Exception as e:
        logger.error(f"Failed to initialize bot: {e}", exc_info=True)
        sys.exit(1)

    dp = Dispatcher()

    # Set bot instance for notifications
    notification_service = NotificationService(bot)

    # Start scheduler for reminders
    try:
        await BotScheduler.start(notification_service)
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}", exc_info=True)
        sys.exit(1)

    # Register routers
    dp.include_router(user_router)
    dp.include_router(barber_router)
    dp.include_router(client_router)

    logger.info("Bot started and listening for messages...")

    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error in bot polling: {e}", exc_info=True)
    finally:
        BotScheduler.stop()
        await bot.session.close()
        MongoDB.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
