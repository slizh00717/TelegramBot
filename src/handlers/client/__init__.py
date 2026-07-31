"""Обработчики для клиентов."""

from .booking import router as booking_router
from .appointments import router as appointments_router
from .profile import router as profile_router

__all__ = [
    "booking_router",
    "appointments_router",
    "profile_router",
]
