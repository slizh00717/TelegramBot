from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from bson.errors import InvalidId
from src.database import get_database


class BaseRepository(ABC):
    """Base repository with common CRUD operations"""

    def __init__(self, collection_name: str, db: Optional[AsyncIOMotorDatabase] = None):
        self.db = db or get_database()
        self.collection = self.db[collection_name]

    @staticmethod
    def _validate_object_id(id: str) -> ObjectId:
        """Validate and convert string to ObjectId"""
        try:
            return ObjectId(id)
        except InvalidId:
            raise ValueError(f"Invalid ObjectId format: {id}")

    async def create(self, data: Dict[str, Any]) -> str:
        """Create a new document"""
        result = await self.collection.insert_one(data)
        return str(result.inserted_id)

    async def find_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        """Find document by ID"""
        try:
            object_id = self._validate_object_id(id)
            return await self.collection.find_one({"_id": object_id})
        except ValueError as e:
            raise ValueError(f"Cannot find document: {str(e)}")

    async def find_many(
        self, query: Dict[str, Any], limit: int = 100, skip: int = 0
    ) -> List[Dict[str, Any]]:
        """Find multiple documents"""
        cursor = self.collection.find(query).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)

    async def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find single document by query"""
        return await self.collection.find_one(query)

    async def update(self, id: str, data: Dict[str, Any]) -> bool:
        """Update document by ID"""
        try:
            object_id = self._validate_object_id(id)
            result = await self.collection.update_one(
                {"_id": object_id}, {"$set": data}
            )
            return result.modified_count > 0
        except ValueError as e:
            raise ValueError(f"Cannot update document: {str(e)}")

    async def update_many(self, query: Dict[str, Any], data: Dict[str, Any]) -> int:
        """Update multiple documents"""
        result = await self.collection.update_many(query, {"$set": data})
        return result.modified_count

    async def delete(self, id: str) -> bool:
        """Delete document by ID"""
        try:
            object_id = self._validate_object_id(id)
            result = await self.collection.delete_one({"_id": object_id})
            return result.deleted_count > 0
        except ValueError as e:
            raise ValueError(f"Cannot delete document: {str(e)}")

    async def delete_many(self, query: Dict[str, Any]) -> int:
        """Delete multiple documents"""
        result = await self.collection.delete_many(query)
        return result.deleted_count

    async def count(self, query: Dict[str, Any] = None) -> int:
        """Count documents"""
        if query is None:
            query = {}
        return await self.collection.count_documents(query)

    async def exists(self, query: Dict[str, Any]) -> bool:
        """Check if document exists"""
        return await self.collection.find_one(query) is not None
