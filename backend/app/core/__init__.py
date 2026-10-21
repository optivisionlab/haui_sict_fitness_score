from app.core.config import settings
from app.core.database import (
    close_async_db,
    configure_redis_notifications,
    db,
    get_async_db,
    get_async_redis,
    get_db,
    get_redis,
)
from app.core.exceptions import setup_exception_handlers
from app.core.middleware import setup_cors, setup_middlewares, ResponseWrapperMiddleware

__all__ = [
    "settings",
    "db",
    "get_db",
    "get_async_db",
    "close_async_db",
    "get_redis",
    "get_async_redis",
    "configure_redis_notifications",
    "setup_cors",
    "setup_middlewares",
    "setup_exception_handlers",
    "ResponseWrapperMiddleware",
]
