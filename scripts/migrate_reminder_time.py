"""
Скрипт для добавления времени напоминания существующим пользователям
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.repositories import UserRepository
from src.utils import logger


async def migrate_reminder_time():
    """Add reminder_time field to users that don't have it"""
    repo = UserRepository()

    # Find all users without reminder_time
    users_without_reminder = await repo.find_many({"reminder_time": {"$exists": False}})

    if not users_without_reminder:
        logger.info("✅ Все пользователи уже имеют время напоминания")
        return

    logger.info(f"🔄 Обновляю {len(users_without_reminder)} пользователей...")

    updated = 0
    for user in users_without_reminder:
        success = await repo.update(str(user["_id"]), {"reminder_time": "09:00"})

        if success:
            updated += 1
            logger.info(f"✅ {user['full_name']} ({user['telegram_id']}) - время: 09:00")
        else:
            logger.error(f"❌ Ошибка при обновлении {user['full_name']}")

    logger.info(f"\n✨ Миграция завершена! Обновлено: {updated} пользователей")


if __name__ == "__main__":
    asyncio.run(migrate_reminder_time())
