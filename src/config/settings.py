from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Settings from environment variables only.
    No .env file support - use export/set commands or Docker environment.

    Usage:
    - Local: export TELEGRAM_BOT_TOKEN="..." && python -m src.main
    - Docker: environment variables in docker-compose.yml or docker run -e
    """

    # Telegram
    telegram_bot_token: str
    telegram_bot_username: str = (
        "YourBotUsername"  # Username бота без @, например: barber_booking_bot
    )
    barber_chat_id: int  # ID чата барбера для уведомлений о новых записях

    # MongoDB
    mongodb_uri: str = "mongodb://localhost:27017"
    database_name: str = "barber_bot"

    # Timezone
    timezone: str = "Europe/Minsk"

    # Logging
    log_level: str = "INFO"

    # Referral program
    referral_bonus_points: int = (
        50  # Бонусные баллы за первый приём приглашённого клиента
    )

    class Config:
        case_sensitive = False
        # Only use environment variables, no .env file
        env_file = None


settings = Settings()
