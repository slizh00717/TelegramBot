import random
import string
from datetime import datetime
from typing import Any

from src.enums import UserRole
from src.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    """Repository for user collection operations.

    Handles all database operations for users including creation, retrieval,
    updates for subscriptions, blocking, referral management, and bonus balances.
    """

    def __init__(self) -> None:
        """Initialize UserRepository with users collection."""
        super().__init__("users")

    @staticmethod
    def generate_referral_code() -> str:
        """Generate a random unique referral code.

        Returns:
            8-character referral code (letters + digits)
        """
        chars = string.ascii_letters + string.digits
        return "".join(random.choices(chars, k=8))

    async def create_user(
        self,
        telegram_id: int,
        full_name: str,
        role: UserRole,
        phone: str | None = None,
        username: str | None = None,
        referral_code: str | None = None,
        referred_by: str | None = None,
    ) -> str:
        """Create a new user with default values.

        Args:
            telegram_id: Unique Telegram user ID
            full_name: User's full name
            role: User role (CLIENT or BARBER)
            phone: Optional phone number
            username: Optional Telegram username
            referral_code: Optional custom referral code (auto-generated if not provided)
            referred_by: Optional user ID who referred this user

        Returns:
            String ID of created user document
        """
        # Generate referral code if not provided
        if not referral_code:
            referral_code = self.generate_referral_code()

        user_data = {
            "telegram_id": telegram_id,
            "full_name": full_name,
            "phone": phone,
            "role": role.value,
            "username": username,
            "is_active": True,
            "is_subscribed": True,
            "is_blocked": False,
            "visit_count": 0 if role == UserRole.CLIENT else None,
            "referral_code": referral_code,
            "referred_by": referred_by,
            "referral_count": 0,
            "bonus_balance": 0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        return await self.create(user_data)

    async def find_by_telegram_id(self, telegram_id: int) -> dict[str, Any] | None:
        """Find user by Telegram ID.

        Args:
            telegram_id: Telegram user ID

        Returns:
            User document or None if not found
        """
        return await self.find_one({"telegram_id": telegram_id})

    async def find_by_phone(self, phone: str) -> dict[str, Any] | None:
        """Find user by phone number.

        Args:
            phone: Phone number to search for

        Returns:
            User document or None if not found
        """
        return await self.find_one({"phone": phone})

    async def find_all_clients(self) -> list[dict[str, Any]]:
        """Find all client users.

        Returns:
            List of all client user documents
        """
        return await self.find_many({"role": UserRole.CLIENT.value})

    async def find_all_subscribed(self) -> list[dict[str, Any]]:
        """Find all users subscribed to notifications.

        Note: This loads ALL subscribed users into memory. For large datasets,
        use find_many with pagination instead.

        Returns:
            List of subscribed user documents
        """
        return await self.find_many({"is_subscribed": True})

    async def find_barbers(self) -> list[dict[str, Any]]:
        """Find all barber users.

        Returns:
            List of all barber user documents
        """
        return await self.find_many({"role": UserRole.BARBER.value})

    async def update_user(self, telegram_id: int, data: dict[str, Any]) -> bool:
        """Update user by telegram_id"""
        user = await self.find_by_telegram_id(telegram_id)
        if not user:
            return False

        data["updated_at"] = datetime.utcnow()
        return await self.update(str(user["_id"]), data)

    async def increment_visit_count(self, telegram_id: int) -> bool:
        """Increment client visit count"""
        user = await self.find_by_telegram_id(telegram_id)
        if not user:
            return False

        await self.collection.update_one(
            {"_id": user["_id"]},
            {"$inc": {"visit_count": 1}, "$set": {"updated_at": datetime.utcnow()}},
        )
        return True

    async def subscribe_user(self, telegram_id: int) -> bool:
        """Subscribe user to notifications"""
        return await self.update_user(telegram_id, {"is_subscribed": True})

    async def unsubscribe_user(self, telegram_id: int) -> bool:
        """Unsubscribe user from notifications"""
        return await self.update_user(telegram_id, {"is_subscribed": False})

    async def block_user(self, user_id: str) -> bool:
        """Block user from receiving notifications"""
        return await self.update(user_id, {"is_blocked": True})

    async def unblock_user(self, user_id: str) -> bool:
        """Unblock user to receive notifications"""
        return await self.update(user_id, {"is_blocked": False})

    async def update_barber_services(self, user_id: str, services: dict[str, float]) -> bool:
        """Update barber services and prices with updated_at timestamp"""
        user = await self.find_by_id(user_id)
        if not user:
            return False

        # Get current services to preserve unmodified values
        current_services = user.get("services", {}) if isinstance(user.get("services"), dict) else {}

        # Build complete services dict, preserving existing values
        new_services = {
            "haircut": (
                services.get("haircut") if services.get("haircut") is not None else current_services.get("haircut")
            ),
            "beard_trim": (
                services.get("beard_trim")
                if services.get("beard_trim") is not None
                else current_services.get("beard_trim")
            ),
            "haircut_and_beard": (
                services.get("haircut_and_beard")
                if services.get("haircut_and_beard") is not None
                else current_services.get("haircut_and_beard")
            ),
            "updated_at": datetime.utcnow(),
        }

        # Update services
        return await self.update(user_id, {"services": new_services})

    async def find_by_referral_code(self, referral_code: str) -> dict[str, Any] | None:
        """Find user by referral code"""
        return await self.find_one({"referral_code": referral_code})

    async def increment_referral_count(self, user_id: str) -> bool:
        """Increment referral count for a user"""
        user = await self.find_by_id(user_id)
        if not user:
            return False

        await self.collection.update_one(
            {"_id": user["_id"]},
            {"$inc": {"referral_count": 1}, "$set": {"updated_at": datetime.utcnow()}},
        )
        return True

    async def get_referrals(self, user_id: str) -> list[dict[str, Any]]:
        """Get all referrals for a user"""
        return await self.find_many({"referred_by": user_id})

    async def add_bonus_balance(self, user_id: str, amount: float) -> bool:
        """Add bonus balance to user"""
        user = await self.find_by_id(user_id)
        if not user:
            return False

        current_balance = user.get("bonus_balance", 0)
        new_balance = current_balance + amount

        return await self.update(user_id, {"bonus_balance": new_balance})

    async def subtract_bonus_balance(self, user_id: str, amount: float) -> bool:
        """Subtract bonus balance from user"""
        user = await self.find_by_id(user_id)
        if not user:
            return False

        current_balance = user.get("bonus_balance", 0)
        if current_balance < amount:
            return False

        new_balance = current_balance - amount
        return await self.update(user_id, {"bonus_balance": new_balance})

    async def update_reminder_time(self, telegram_id: int, reminder_time: str) -> bool:
        """Update reminder time for user (format HH:MM)"""
        return await self.update_user(telegram_id, {"reminder_time": reminder_time})
