"""Database engine, session management, and initialization."""

import logging

from sqlalchemy.exc import OperationalError
from sqlalchemy_utils import create_database, database_exists
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings

logger = logging.getLogger(__name__)


def _make_engine(url: str):
    return create_engine(url, pool_pre_ping=True)


engine = _make_engine(settings.DATABASE_URL)


def get_db():
    """FastAPI dependency that yields a SQLModel session."""
    with Session(engine) as session:
        yield session


def init_db(auto_create: bool = True) -> None:
    """Initialize DB: optionally create the database, then create all tables."""
    global engine

    if auto_create:
        try:
            if not database_exists(settings.DATABASE_URL):
                logger.info("Database not found; creating: %s", settings.DATABASE_URL)
                create_database(settings.DATABASE_URL)
                logger.info("Database created successfully")
                engine = _make_engine(settings.DATABASE_URL)
        except Exception:
            logger.exception("Failed to create database with sqlalchemy-utils")

    try:
        with engine.connect() as conn:
            pass
    except OperationalError:
        logger.exception("Operational error connecting to DB; tables may not be created")

    SQLModel.metadata.create_all(engine)
