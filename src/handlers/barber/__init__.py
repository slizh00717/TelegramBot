"""Обработчики для барберов."""

from .schedule import router as schedule_router
from .profile import router as profile_router
from .services import router as services_router
from .clients import router as clients_router
from .appointments import router as appointments_router

__all__ = [
    "schedule_router",
    "profile_router",
    "services_router",
    "clients_router",
    "appointments_router",
]
