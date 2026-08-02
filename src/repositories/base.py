from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from bson.errors import InvalidId
from src.database import get_database


class BaseRepository(ABC):
    """Base repository class providing common CRUD operations.

    This abstract class provides a standard async interface for MongoDB operations
    using the motor library (async MongoDB driver). All subclasses inherit these
    base operations for their specific collections.

    Attributes:
        db: Async MongoDB database instance (motor)
        collection: Async MongoDB collection instance (motor)
    """

    def __init__(
        self, collection_name: str, db: Optional[AsyncIOMotorDatabase] = None
    ) -> None:
        """Initialize repository with collection name.

        Args:
            collection_name: Name of the MongoDB collection
            db: Async MongoDB database instance (default: get_database())
        """
        self.db: AsyncIOMotorDatabase = db or get_database()
        self.collection = self.db[collection_name]

    @staticmethod
    def _validate_object_id(id: str) -> ObjectId:
        """Validate and convert string to ObjectId.

        Args:
            id: String representation of ObjectId

        Returns:
            Valid ObjectId instance

        Raises:
            ValueError: If id is not a valid ObjectId format
        """
        try:
            return ObjectId(id)
        except InvalidId:
            raise ValueError(f"Invalid ObjectId format: {id}")

    async def create(self, data: Dict[str, Any]) -> str:
        """Create a new document in the collection.

        Args:
            data: Document data to insert

        Returns:
            String ID of the created document

        Raises:
            Exception: If insert operation fails
        """
        result = await self.collection.insert_one(data)
        return str(result.inserted_id)

    async def find_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        """Find document by MongoDB ObjectId.

        Args:
            id: Document ID in string format

        Returns:
            Document dict or None if not found

        Raises:
            ValueError: If id is not a valid ObjectId format
        """
        try:
            object_id = self._validate_object_id(id)
            return await self.collection.find_one({"_id": object_id})
        except ValueError as e:
            raise ValueError(f"Cannot find document: {str(e)}")

    async def find_many(
        self, query: Dict[str, Any], limit: Optional[int] = None, skip: int = 0
    ) -> List[Dict[str, Any]]:
        """Find multiple documents matching query.

        Args:
            query: MongoDB query filter
            limit: Maximum documents to return (None = unlimited)
            skip: Number of documents to skip for pagination

        Returns:
            List of matching documents
        """
        cursor = self.collection.find(query).skip(skip)
        if limit is not None:
            cursor = cursor.limit(limit)
            return await cursor.to_list(length=limit)
        else:
            return await cursor.to_list(length=None)

    async def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find first document matching query.

        Args:
            query: MongoDB query filter

        Returns:
            First matching document or None if not found
        """
        return await self.collection.find_one(query)

    async def update(self, id: str, data: Dict[str, Any]) -> bool:
        """Update document by ID with provided data.

        Args:
            id: Document ID in string format
            data: Fields to update

        Returns:
            True if document was modified, False otherwise

        Raises:
            ValueError: If id is not a valid ObjectId format
        """
        try:
            object_id = self._validate_object_id(id)
            result = await self.collection.update_one(
                {"_id": object_id}, {"$set": data}
            )
            return result.modified_count > 0
        except ValueError as e:
            raise ValueError(f"Cannot update document: {str(e)}")

    async def update_many(self, query: Dict[str, Any], data: Dict[str, Any]) -> int:
        """Update multiple documents matching query.

        Args:
            query: MongoDB query filter
            data: Fields to update

        Returns:
            Number of modified documents
        """
        result = await self.collection.update_many(query, {"$set": data})
        return result.modified_count

    async def delete(self, id: str) -> bool:
        """Delete document by ID.

        Args:
            id: Document ID in string format

        Returns:
            True if document was deleted, False if not found

        Raises:
            ValueError: If id is not a valid ObjectId format
        """
        try:
            object_id = self._validate_object_id(id)
            result = await self.collection.delete_one({"_id": object_id})
            return result.deleted_count > 0
        except ValueError as e:
            raise ValueError(f"Cannot delete document: {str(e)}")

    async def delete_many(self, query: Dict[str, Any]) -> int:
        """Delete multiple documents matching query.

        Args:
            query: MongoDB query filter

        Returns:
            Number of deleted documents
        """
        result = await self.collection.delete_many(query)
        return result.deleted_count

    async def count(self, query: Optional[Dict[str, Any]] = None) -> int:
        """Count documents matching query.

        Args:
            query: MongoDB query filter (default: empty = all documents)

        Returns:
            Number of matching documents
        """
        if query is None:
            query = {}
        return await self.collection.count_documents(query)

    async def exists(self, query: Dict[str, Any]) -> bool:
        """Check if any document exists matching query.

        Args:
            query: MongoDB query filter

        Returns:
            True if at least one document matches, False otherwise
        """
        return await self.collection.find_one(query) is not None
