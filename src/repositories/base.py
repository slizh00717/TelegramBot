from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pymongo.database import Database
from bson import ObjectId
from src.database import get_database


class BaseRepository(ABC):
    """Base repository with common CRUD operations"""

    def __init__(self, collection_name: str, db: Optional[Database] = None):
        self.db = db or get_database()
        self.collection = self.db[collection_name]

    async def create(self, data: Dict[str, Any]) -> str:
        """Create a new document"""
        result = self.collection.insert_one(data)
        return str(result.inserted_id)

    async def find_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        """Find document by ID"""
        return self.collection.find_one({"_id": ObjectId(id)})

    async def find_many(
        self, query: Dict[str, Any], limit: int = 100, skip: int = 0
    ) -> List[Dict[str, Any]]:
        """Find multiple documents"""
        return list(self.collection.find(query).skip(skip).limit(limit))

    async def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find single document by query"""
        return self.collection.find_one(query)

    async def update(self, id: str, data: Dict[str, Any]) -> bool:
        """Update document by ID"""
        result = self.collection.update_one({"_id": ObjectId(id)}, {"$set": data})
        return result.modified_count > 0

    async def update_many(self, query: Dict[str, Any], data: Dict[str, Any]) -> int:
        """Update multiple documents"""
        result = self.collection.update_many(query, {"$set": data})
        return result.modified_count

    async def delete(self, id: str) -> bool:
        """Delete document by ID"""
        result = self.collection.delete_one({"_id": ObjectId(id)})
        return result.deleted_count > 0

    async def delete_many(self, query: Dict[str, Any]) -> int:
        """Delete multiple documents"""
        result = self.collection.delete_many(query)
        return result.deleted_count

    async def count(self, query: Dict[str, Any] = None) -> int:
        """Count documents"""
        if query is None:
            query = {}
        return self.collection.count_documents(query)

    async def exists(self, query: Dict[str, Any]) -> bool:
        """Check if document exists"""
        return self.collection.find_one(query) is not None
