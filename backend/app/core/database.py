"""Small, explicit PyMongo repository used by the API routers."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from bson import ObjectId
from pymongo import ASCENDING, MongoClient

from app.core.config import settings

logger = logging.getLogger(__name__)
client = MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=3000)
database = client[settings.MONGODB_DB]


def object_id(value: str) -> ObjectId:
    if not ObjectId.is_valid(value):
        raise ValueError("Invalid MongoDB identifier")
    return ObjectId(value)


def clean(document: dict[str, Any] | None) -> dict[str, Any] | None:
    if document is None:
        return None
    document = dict(document)
    identifier = document.pop("_id", None)
    document["id"] = str(identifier) if identifier is not None else document.get("id")
    return document


def collection(name: str):
    return database[name]


def get_db():
    return database


def init_db() -> None:
    database.users.create_index("email", unique=True, sparse=True)
    database.users.create_index("username", unique=True, sparse=True)
    database.sports.create_index("code", unique=True)
    database.enrollments.create_index([("courseId", ASCENDING), ("userId", ASCENDING)], unique=True)
    logger.info("MongoDB indexes initialized for %s", settings.MONGODB_DB)


def now() -> datetime:
    return datetime.utcnow()
