from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message

from src.utils import logger


async def safe_edit_text(message: Message, text: str, reply_markup=None, parse_mode="HTML") -> bool:
    """
    Safely edit message text, ignoring 'message not modified' errors.

    Args:
        message: Message object to edit
        text: New text content
        reply_markup: Optional inline keyboard
        parse_mode: Parse mode (default: HTML)

    Returns:
        True if successful, False if error (excluding 'not modified')
    """
    try:
        await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        return True
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Это нормально - сообщение уже имеет такой же текст
            logger.debug(f"Message not modified: {e}")
            return True
        else:
            logger.error(f"Telegram error while editing message: {e}")
            raise
