import logging
from collections.abc import Callable
from functools import wraps

from aiogram.types import CallbackQuery, Message

from src.enums import UserRole
from src.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)


def require_role(*allowed_roles: UserRole):
    """Decorator to check if user has required role"""

    def decorator(handler: Callable):
        @wraps(handler)
        async def wrapper(update: Message | CallbackQuery, *args, **kwargs):
            user_repo = UserRepository()
            telegram_id = update.from_user.id

            user = await user_repo.find_by_telegram_id(telegram_id)
            if not user:
                await update.answer(
                    "❌ Користувач не зареєстрований. Використайте /start"
                )
                return

            if user["role"] not in [role.value for role in allowed_roles]:
                await update.answer("❌ У вас немає прав для цієї операції.")
                return

            return await handler(update, *args, **kwargs)

        return wrapper

    return decorator


def require_registration(handler: Callable):
    """Decorator to check if user is registered"""

    @wraps(handler)
    async def wrapper(update: Message | CallbackQuery, *args, **kwargs):
        user_repo = UserRepository()
        telegram_id = update.from_user.id

        user = await user_repo.find_by_telegram_id(telegram_id)
        if not user:
            await update.answer("❌ Користувач не зареєстрований. Використайте /start")
            return

        return await handler(update, *args, **kwargs)

    return wrapper


def log_handler_error(handler: Callable):
    """Decorator to log errors in handlers"""

    @wraps(handler)
    async def wrapper(*args, **kwargs):
        try:
            return await handler(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in handler {handler.__name__}: {e}", exc_info=True)
            raise

    return wrapper
