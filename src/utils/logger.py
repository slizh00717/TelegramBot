import logging
import sys
from src.config import settings


def setup_logger():
    """Configure logging for the application"""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("bot.log")],
    )
    return logging.getLogger(__name__)


logger = setup_logger()
