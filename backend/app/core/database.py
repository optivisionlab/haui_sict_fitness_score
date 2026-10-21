import asyncio
from functools import lru_cache
from typing import Optional

import redis
from pymongo import AsyncMongoClient, MongoClient
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.database import Database
from redis import asyncio as aioredis

from app.core.config import settings

# MongoDB
_mongo_client = MongoClient(
    settings.MONGODB_URI,
    serverSelectionTimeoutMS=3000,
    username=settings.MONGODB_USERNAME,
    password=settings.MONGODB_PASSWORD,
)
db: Database = _mongo_client[settings.MONGODB_DB]


def get_db() -> Database:
    return db


# MongoDB async: dùng trong coroutine (outbox, worker pool, dependency xác thực) để không chặn event loop.
# Client gắn với event loop đầu tiên dùng nó, nên lifespan đóng client khi tắt.
_async_mongo_client: Optional[AsyncMongoClient] = None
_async_mongo_loop: Optional[asyncio.AbstractEventLoop] = None


def get_async_db() -> AsyncDatabase:
    global _async_mongo_client, _async_mongo_loop
    try:
        loop: Optional[asyncio.AbstractEventLoop] = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    # Event loop khác (TestClient, script gọi asyncio.run nhiều lần) thì tạo client mới cho loop đó
    if _async_mongo_client is None or (loop is not None and loop is not _async_mongo_loop):
        _async_mongo_loop = loop
        _async_mongo_client = AsyncMongoClient(
            settings.MONGODB_URI,
            serverSelectionTimeoutMS=3000,
            username=settings.MONGODB_USERNAME,
            password=settings.MONGODB_PASSWORD,
        )
    return _async_mongo_client[settings.MONGODB_DB]


async def close_async_db() -> None:
    global _async_mongo_client
    if _async_mongo_client is not None:
        client, _async_mongo_client = _async_mongo_client, None
        await client.close()


# Redis
def _get_redis_kwargs() -> dict:
    kwargs = {
        "host": settings.REDIS_HOST,
        "port": settings.REDIS_PORT,
        "db": settings.REDIS_DB,
        "decode_responses": settings.REDIS_DECODE_RESPONSES,
    }
    if settings.REDIS_PASSWORD:
        kwargs["password"] = settings.REDIS_PASSWORD
    return kwargs


@lru_cache
def get_redis() -> redis.Redis:
    return redis.Redis(**_get_redis_kwargs())


@lru_cache
def get_async_redis() -> aioredis.Redis:
    return aioredis.Redis(**_get_redis_kwargs())


def configure_redis_notifications(events: Optional[str] = None) -> None:
    desired = events or settings.REDIS_NOTIFY_EVENTS
    try:
        r = get_redis()
        current = (r.config_get("notify-keyspace-events") or {}).get("notify-keyspace-events")
        if current != desired:
            r.config_set("notify-keyspace-events", desired)
    except Exception:
        pass
