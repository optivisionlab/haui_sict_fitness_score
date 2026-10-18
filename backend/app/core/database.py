from functools import lru_cache
from typing import Optional

import redis
from pymongo import MongoClient
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
