from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from src.config import settings
import logging

logger = logging.getLogger(__name__)


class MongoDB:
    _client: AsyncIOMotorClient | None = None
    _db: AsyncIOMotorDatabase | None = None

    @classmethod
    def connect(cls) -> AsyncIOMotorDatabase:
        """Connect to MongoDB and return database instance"""
        if cls._client is None:
            try:
                cls._client = AsyncIOMotorClient(settings.mongodb_uri)
                cls._db = cls._client[settings.database_name]
                logger.info(f"Connected to MongoDB: {settings.database_name}")
            except Exception as e:
                logger.error(f"Failed to connect to MongoDB: {e}")
                raise

        return cls._db

    @classmethod
    def disconnect(cls) -> None:
        """Disconnect from MongoDB"""
        if cls._client is not None:
            cls._client.close()
            cls._client = None
            cls._db = None
            logger.info("Disconnected from MongoDB")

    @classmethod
    def get_db(cls) -> AsyncIOMotorDatabase:
        """Get database instance, connect if needed"""
        if cls._db is None:
            cls.connect()
        return cls._db

    @classmethod
    def get_client(cls) -> AsyncIOMotorClient:
        """Get MongoDB client instance for transactions"""
        if cls._client is None:
            cls.connect()
        return cls._client


def get_database() -> AsyncIOMotorDatabase:
    """Dependency injection for database"""
    return MongoDB.get_db()


def get_mongo_client() -> AsyncIOMotorClient:
    """Get MongoDB client for transactions"""
    return MongoDB.get_client()
