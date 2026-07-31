"""
Скрипт для добавления реферальных кодов существующим пользователям
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.repositories import UserRepository
from src.utils import logger
import string
import random


def generate_referral_code() -> str:
    """Generate a unique referral code"""
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=8))


async def migrate_referral_codes():
    """Add referral codes to users that don't have them"""
    repo = UserRepository()

    # Find all users without referral codes
    users_without_codes = await repo.find_many({"referral_code": {"$exists": False}})

    if not users_without_codes:
        logger.info("✅ Все пользователи уже имеют реферальные коды")
        return

    logger.info(f"🔄 Обновляю {len(users_without_codes)} пользователей...")

    updated = 0
    for user in users_without_codes:
        referral_code = generate_referral_code()
        success = await repo.update(str(user["_id"]), {"referral_code": referral_code})

        if success:
            updated += 1
            logger.info(
                f"✅ {user['full_name']} ({user['telegram_id']}) - код: {referral_code}"
            )
        else:
            logger.error(f"❌ Ошибка при обновлении {user['full_name']}")

    logger.info(f"\n✨ Миграция завершена! Обновлено: {updated} пользователей")


if __name__ == "__main__":
    asyncio.run(migrate_referral_codes())
