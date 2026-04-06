"""Redis client management: sync and async clients, keyspace notification config."""

import logging
from functools import lru_cache

import redis
from redis import asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)


@lru_cache()
def get_redis_client() -> redis.Redis:
    """Return a configured synchronous Redis client (cached singleton).

    Pings once during creation so startup issues are logged early.
    """
    kwargs: dict = {
        "host": settings.REDIS_HOST,
        "port": settings.REDIS_PORT,
        "db": settings.REDIS_DB,
        "decode_responses": settings.REDIS_DECODE_RESPONSES,
    }
    if settings.REDIS_PASSWORD:
        kwargs["password"] = settings.REDIS_PASSWORD

    client = redis.Redis(**kwargs)

    try:
        client.ping()
        logger.info("Connected to Redis at %s:%s db=%s", settings.REDIS_HOST, settings.REDIS_PORT, settings.REDIS_DB)
    except Exception:
        logger.exception("Failed to ping Redis at %s:%s", settings.REDIS_HOST, settings.REDIS_PORT)

    return client


@lru_cache()
def get_async_redis() -> aioredis.Redis:
    """Return a configured async Redis client (cached singleton)."""
    kwargs: dict = {
        "host": settings.REDIS_HOST,
        "port": settings.REDIS_PORT,
        "db": settings.REDIS_DB,
        "decode_responses": settings.REDIS_DECODE_RESPONSES,
    }
    if settings.REDIS_PASSWORD:
        kwargs["password"] = settings.REDIS_PASSWORD

    client = aioredis.Redis(**kwargs)
    logger.info("Async Redis client created for %s:%s db=%s", settings.REDIS_HOST, settings.REDIS_PORT, settings.REDIS_DB)
    return client


def configure_redis_notifications(desired: str | None = None) -> None:
    """Ensure the Redis server's ``notify-keyspace-events`` matches *desired*."""
    desired = desired or settings.REDIS_NOTIFY_EVENTS
    try:
        client = get_redis_client()
        current = client.config_get("notify-keyspace-events") or {}
        cur_val = current.get("notify-keyspace-events")
        if cur_val == desired:
            logger.info("Redis notify-keyspace-events already set to %s", cur_val)
            return
        client.config_set("notify-keyspace-events", desired)
        logger.info("Set Redis notify-keyspace-events: %s -> %s", cur_val, desired)
    except Exception:
        logger.exception("Failed to configure Redis notify-keyspace-events to %s", desired)
