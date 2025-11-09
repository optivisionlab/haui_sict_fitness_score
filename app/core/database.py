from sqlmodel import Session, create_engine, SQLModel
from .config import settings
import logging
from sqlalchemy.exc import OperationalError
from sqlalchemy_utils import database_exists, create_database

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
    """Initialize DB and create tables. When `auto_create` is True the function
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