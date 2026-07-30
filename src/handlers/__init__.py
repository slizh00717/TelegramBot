from .user_handlers import router as user_router
from .barber_handlers import router as barber_router
from .client_handlers import router as client_router

__all__ = ["user_router", "barber_router", "client_router"]
