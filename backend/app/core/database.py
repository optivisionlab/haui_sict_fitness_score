from sqlmodel import Session, create_engine, SQLModel
from .config import settings
import logging
from sqlalchemy.exc import OperationalError
from sqlalchemy_utils import database_exists, create_database
from functools import lru_cache
import redis
from redis import asyncio as aioredis

logger = logging.getLogger(__name__)


# Simple engine factory so we can recreate after DB creation
def _make_engine(url: str):
    return create_engine(url, pool_pre_ping=True)


# Module-level engine used by get_db; recreated in init_db if DB was just created
engine = _make_engine(settings.DATABASE_URL)


def get_db():
    with Session(engine) as session:
        yield session


def init_db(auto_create: bool = True):
    """
    Initialize DB and create tables. When `auto_create` is True the function
    will create the database (via sqlalchemy-utils) if it doesn't exist.
    """
    global engine

    if auto_create:
        try:
            if not database_exists(settings.DATABASE_URL):
                logger.info("Database not found; creating: %s", settings.DATABASE_URL)
                create_database(settings.DATABASE_URL)
                logger.info("Database created: %s", settings.DATABASE_URL)
                # recreate engine to pick up the new DB
                engine = _make_engine(settings.DATABASE_URL)
        except Exception:
            logger.exception("Failed to create database with sqlalchemy-utils")

    # Try a quick connect to surface connection issues early (logged)
    try:
        with engine.connect() as conn:
            pass
    except OperationalError:
        logger.exception("Operational error connecting to DB; tables may not be created")

    # Create tables (no-op if already present)
    SQLModel.metadata.create_all(engine)


@lru_cache()
def get_redis_client() -> redis.Redis:
    """
    Return a configured redis.Redis client using settings.

    The client is pinged once during creation so startup issues are logged early.
    This function is cached so the same client instance is reused across imports.
    """

    # Dùng dict để chỉ thêm password nếu có
    redis_kwargs = {
        "host": settings.REDIS_HOST,
        "port": settings.REDIS_PORT,
        "db": settings.REDIS_DB,
        "decode_responses": settings.REDIS_DECODE_RESPONSES,
    }
    if getattr(settings, "REDIS_PASSWORD", None):  # chỉ thêm nếu tồn tại
        redis_kwargs["password"] = settings.REDIS_PASSWORD

    client = redis.Redis(**redis_kwargs)

    try:
        client.ping()
        logger.info(
            "Connected to Redis at %s:%s db=%s",
            settings.REDIS_HOST,
            settings.REDIS_PORT,
            settings.REDIS_DB,
        )
    except Exception:
        logger.exception(
            "Failed to ping Redis at %s:%s",
            settings.REDIS_HOST,
            settings.REDIS_PORT,
        )
    return client


@lru_cache()
def get_async_redis() -> aioredis.Redis:
    """
    Return a configured asyncio Redis client (redis.asyncio.Redis).
    """

    redis_kwargs = {
        "host": settings.REDIS_HOST,
        "port": settings.REDIS_PORT,
        "db": settings.REDIS_DB,
        "decode_responses": settings.REDIS_DECODE_RESPONSES,
    }

    if getattr(settings, "REDIS_PASSWORD", None):
        redis_kwargs["password"] = settings.REDIS_PASSWORD

    client = aioredis.Redis(**redis_kwargs)
    logger.info(
        "Async Redis client created for %s:%s db=%s",
        settings.REDIS_HOST,
        settings.REDIS_PORT,
        settings.REDIS_DB,
    )
    return client


def configure_redis_notifications(desired: str | None = None) -> None:
    """
    Ensure the Redis server's `notify-keyspace-events` setting matches `desired`.
    """
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
