from typing import Optional, Dict, Any
from src.repositories import UserRepository
from src.enums import UserRole
from src.utils import logger, validate_phone, normalize_phone


class UserService:
    def __init__(self):
        self.user_repo = UserRepository()

    async def register_user(
        self,
        telegram_id: int,
        full_name: str,
        role: UserRole,
        phone: Optional[str] = None,
        username: Optional[str] = None,
        referral_code_from: Optional[str] = None,
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
            logger.warning(f"Invalid phone number: {phone}")
            return None

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
            logger.info(
                f"Registered user {user_id} (telegram_id: {telegram_id}) referred by {referred_by}"
            )
        else:
            logger.info(
                f"Registered user {user_id} (telegram_id: {telegram_id}, role: {role})"
            )

        return user_id

    async def get_user(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Get user by Telegram ID"""
        return await self.user_repo.find_by_telegram_id(telegram_id)

    async def update_user_profile(
        self,
        telegram_id: int,
        full_name: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> bool:
        """Update user profile"""
        user = await self.get_user(telegram_id)
        if not user:
            return False

        update_data = {}
        if full_name:
            update_data["full_name"] = full_name
        if phone:
            if not validate_phone(phone):
                logger.warning(f"Invalid phone number: {phone}")
                return False
            update_data["phone"] = normalize_phone(phone)

        return await self.user_repo.update_user(telegram_id, update_data)

    async def subscribe_to_notifications(self, telegram_id: int) -> bool:
        """Subscribe user to notifications"""
        return await self.user_repo.subscribe_user(telegram_id)

    async def unsubscribe_from_notifications(self, telegram_id: int) -> bool:
        """Unsubscribe user from notifications"""
        return await self.user_repo.unsubscribe_user(telegram_id)

    async def get_all_subscribed_clients(self) -> list[Dict[str, Any]]:
        """Get all subscribed clients for notifications"""
        clients = await self.user_repo.find_all_clients()
        return [c for c in clients if c.get("is_subscribed", True)]

    async def increment_visit_count(self, telegram_id: int) -> bool:
        """Increment client's visit count"""
        return await self.user_repo.increment_visit_count(telegram_id)

    async def get_barbers(self) -> list[Dict[str, Any]]:
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
        return user and user.get("is_blocked", False) if user else False

    async def update_barber_services(
        self,
        barber_id: str,
        haircut: Optional[float] = None,
        beard_trim: Optional[float] = None,
        haircut_and_beard: Optional[float] = None,
    ) -> bool:
        """Update barber services and prices"""
        # Get current services
        user = await self.user_repo.find_by_id(barber_id)
        current_services = user.get("services", {}) if user else {}

        # Build complete services dict
        services = {
            "haircut": (
                haircut if haircut is not None else current_services.get("haircut")
            ),
            "beard_trim": (
                beard_trim
                if beard_trim is not None
                else current_services.get("beard_trim")
            ),
            "haircut_and_beard": (
                haircut_and_beard
                if haircut_and_beard is not None
                else current_services.get("haircut_and_beard")
            ),
        }

        return await self.user_repo.update_barber_services(barber_id, services)

    async def get_barber_services(self, barber_id: str) -> Optional[Dict[str, Any]]:
        """Get barber services and prices"""
        user = await self.user_repo.find_by_id(barber_id)
        if user:
            return user.get("services", {})
        return None

    async def get_referral_code(self, telegram_id: int) -> Optional[str]:
        """Get referral code for a user"""
        user = await self.get_user(telegram_id)
        if user:
            return user.get("referral_code")
        return None

    async def get_referral_stats(self, telegram_id: int) -> Optional[Dict[str, Any]]:
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

    async def get_referrer_info(self, telegram_id: int) -> Optional[Dict[str, Any]]:
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
