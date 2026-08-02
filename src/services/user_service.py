from typing import Any

from src.enums import UserRole
from src.repositories import UserRepository
from src.utils import logger, normalize_phone, validate_phone


class UserService:
    """Service layer for user-related operations.

    Provides business logic for user registration, profile management, role checking,
    referral tracking, and bonus balance management. Coordinates between handlers
    and the UserRepository.

    Attributes:
        user_repo: UserRepository instance for database operations
    """

    def __init__(self) -> None:
        """Initialize UserService with UserRepository."""
        self.user_repo: UserRepository = UserRepository()

    async def register_user(
        self,
        telegram_id: int,
        full_name: str,
        role: UserRole,
        phone: str | None = None,
        username: str | None = None,
        referral_code_from: str | None = None,
    ) -> str:
        """
        Register a new user.

        Args:
            telegram_id: User's Telegram ID
            full_name: User's full name
            role: User's role (BARBER or CLIENT)
            phone: User's phone number (optional)
            username: User's Telegram username (optional)
            referral_code_from: Referral code from the inviting user (optional)

        Returns:
            User ID
        """
        # Check if user already exists
        existing_user = await self.user_repo.find_by_telegram_id(telegram_id)
        if existing_user:
            logger.warning(f"User {telegram_id} already exists")
            return str(existing_user["_id"])

        # Validate and normalize phone
        if phone and not validate_phone(phone):
            raise ValueError(f"Invalid phone number format: {phone}")

        normalized_phone = normalize_phone(phone) if phone else None

        # Find referrer if referral code provided
        referred_by = None
        if referral_code_from:
            referrer = await self.user_repo.find_by_referral_code(referral_code_from)
            if referrer:
                referred_by = str(referrer["_id"])

        # Create user (repo will generate referral code automatically)
        user_id = await self.user_repo.create_user(
            telegram_id=telegram_id,
            full_name=full_name,
            role=role,
            phone=normalized_phone,
            username=username,
            referred_by=referred_by,
        )

        # Increment referral count for referrer if applicable
        if referred_by:
            await self.user_repo.increment_referral_count(referred_by)
            logger.info(f"Registered user {user_id} (telegram_id: {telegram_id}) referred by {referred_by}")
        else:
            logger.info(f"Registered user {user_id} (telegram_id: {telegram_id}, role: {role})")

        return user_id

    async def get_user(self, telegram_id: int) -> dict[str, Any] | None:
        """Get user by Telegram ID.

        Args:
            telegram_id: Telegram user ID

        Returns:
            User document or None if not found
        """
        return await self.user_repo.find_by_telegram_id(telegram_id)

    async def update_user_profile(
        self,
        telegram_id: int,
        full_name: str | None = None,
        phone: str | None = None,
        address: str | None = None,
    ) -> bool:
        """Update user profile with partial updates.

        Only non-None fields are updated. Validates phone format if provided.

        Args:
            telegram_id: Telegram user ID
            full_name: New full name (optional)
            phone: New phone number (optional, validated)
            address: New address (optional)

        Returns:
            True if update succeeded, False if user not found

        Raises:
            ValueError: If phone format is invalid
        """
        user = await self.get_user(telegram_id)
        if not user:
            return False

        update_data = {}
        if full_name:
            update_data["full_name"] = full_name
        if phone:
            if not validate_phone(phone):
                raise ValueError(f"Invalid phone number format: {phone}")
            update_data["phone"] = normalize_phone(phone)
        if address:
            update_data["address"] = address

        return await self.user_repo.update_user(telegram_id, update_data)

    async def subscribe_to_notifications(self, telegram_id: int) -> bool:
        """Subscribe user to notifications.

        Args:
            telegram_id: Telegram user ID

        Returns:
            True if subscription updated, False if user not found
        """
        return await self.user_repo.subscribe_user(telegram_id)

    async def unsubscribe_from_notifications(self, telegram_id: int) -> bool:
        """Unsubscribe user from notifications.

        Args:
            telegram_id: Telegram user ID

        Returns:
            True if subscription updated, False if user not found
        """
        return await self.user_repo.unsubscribe_user(telegram_id)

    async def get_all_subscribed_clients(self) -> list[dict[str, Any]]:
        """Get all subscribed clients for notifications"""
        clients = await self.user_repo.find_all_clients()
        return [c for c in clients if c.get("is_subscribed", True)]

    async def increment_visit_count(self, telegram_id: int) -> bool:
        """Increment client's visit count"""
        return await self.user_repo.increment_visit_count(telegram_id)

    async def get_barbers(self) -> list[dict[str, Any]]:
        """Get all barbers"""
        return await self.user_repo.find_barbers()

    async def is_barber(self, telegram_id: int) -> bool:
        """Check if user is a barber"""
        user = await self.get_user(telegram_id)
        return user and user.get("role") == UserRole.BARBER.value

    async def is_client(self, telegram_id: int) -> bool:
        """Check if user is a client"""
        user = await self.get_user(telegram_id)
        return user and user.get("role") == UserRole.CLIENT.value

    async def delete_user(self, telegram_id: int) -> bool:
        """Delete user account"""
        user = await self.get_user(telegram_id)
        if not user:
            return False
        return await self.user_repo.delete(str(user["_id"]))

    async def block_user(self, user_id: str) -> bool:
        """Block user from receiving notifications"""
        return await self.user_repo.block_user(user_id)

    async def unblock_user(self, user_id: str) -> bool:
        """Unblock user to receive notifications"""
        return await self.user_repo.unblock_user(user_id)

    async def is_user_blocked(self, user_id: str) -> bool:
        """Check if user is blocked"""
        user = await self.user_repo.find_by_id(user_id)
        if not user:
            return False
        return user.get("is_blocked", False)

    async def update_barber_services(
        self,
        barber_id: str,
        haircut: float | None = None,
        beard_trim: float | None = None,
        haircut_and_beard: float | None = None,
    ) -> bool:
        """Update barber services and prices"""
        # Get current services
        user = await self.user_repo.find_by_id(barber_id)
        current_services = user.get("services", {}) if user else {}

        # Build complete services dict
        services = {
            "haircut": (haircut if haircut is not None else current_services.get("haircut")),
            "beard_trim": (beard_trim if beard_trim is not None else current_services.get("beard_trim")),
            "haircut_and_beard": (
                haircut_and_beard if haircut_and_beard is not None else current_services.get("haircut_and_beard")
            ),
        }

        return await self.user_repo.update_barber_services(barber_id, services)

    async def get_barber_services(self, barber_id: str) -> dict[str, Any] | None:
        """Get barber services and prices"""
        user = await self.user_repo.find_by_id(barber_id)
        if user:
            return user.get("services", {})
        return None

    async def get_referral_code(self, telegram_id: int) -> str | None:
        """Get referral code for a user"""
        user = await self.get_user(telegram_id)
        if user:
            return user.get("referral_code")
        return None

    async def get_referral_stats(self, telegram_id: int) -> dict[str, Any] | None:
        """Get referral statistics for a user"""
        user = await self.get_user(telegram_id)
        if not user:
            return None

        referrals = await self.user_repo.get_referrals(str(user["_id"]))
        return {
            "referral_code": user.get("referral_code"),
            "referral_count": user.get("referral_count", 0),
            "referrals": referrals,
        }

    async def get_referrer_info(self, telegram_id: int) -> dict[str, Any] | None:
        """Get info about who referred this user"""
        user = await self.get_user(telegram_id)
        if not user or not user.get("referred_by"):
            return None

        referrer = await self.user_repo.find_by_id(user.get("referred_by"))
        if referrer:
            return {"name": referrer.get("full_name"), "phone": referrer.get("phone")}
        return None

    async def add_bonus_balance(self, telegram_id: int, amount: float) -> bool:
        """Add bonus balance to user"""
        user = await self.get_user(telegram_id)
        if not user:
            return False
        return await self.user_repo.add_bonus_balance(str(user["_id"]), amount)

    async def subtract_bonus_balance(self, telegram_id: int, amount: float) -> bool:
        """Subtract bonus balance from user"""
        user = await self.get_user(telegram_id)
        if not user:
            return False
        return await self.user_repo.subtract_bonus_balance(str(user["_id"]), amount)

    async def get_bonus_balance(self, telegram_id: int) -> float:
        """Get bonus balance for user"""
        user = await self.get_user(telegram_id)
        if user:
            return user.get("bonus_balance", 0)
        return 0

    async def update_reminder_time(self, telegram_id: int, reminder_time: str) -> bool:
        """Update reminder time for user"""
        return await self.user_repo.update_reminder_time(telegram_id, reminder_time)
