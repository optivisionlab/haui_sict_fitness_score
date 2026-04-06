"""User business logic: CRUD, authentication, registration."""

import logging
from typing import Optional

from sqlalchemy import text
from sqlmodel import Session, select

from app.core.exceptions import (
    AlreadyExistsException,
    InvalidInputException,
    NotFoundException,
)
from app.core.security import hash_password, verify_password
from app.models.user import User, UserStatus
from app.schemas.users import UserCreate, UserUpdate

logger = logging.getLogger(__name__)


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.get(User, user_id)


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.exec(select(User).where(User.email == email)).first()


def get_user_by_username(db: Session, user_name: str) -> Optional[User]:
    return db.exec(select(User).where(User.user_name == user_name)).first()


def list_users(db: Session, skip: int = 0, limit: int = 100) -> list[User]:
    return db.exec(select(User).offset(skip).limit(limit)).all()


def register_user(db: Session, user_in: UserCreate) -> User:
    """Register a new user with uniqueness checks and password hashing."""
    if not user_in.password:
        raise InvalidInputException("Password is required")

    email = user_in.email.strip() if user_in.email else None
    user_name = user_in.user_name.strip() if user_in.user_name else None

    if email and get_user_by_email(db, email):
        raise AlreadyExistsException("The user with this email already exists.")

    if user_name and get_user_by_username(db, user_name):
        raise AlreadyExistsException("The user with this username already exists.")

    payload = user_in.model_dump(exclude={"password"})
    if email is not None:
        payload["email"] = email
    if user_name is not None:
        payload["user_name"] = user_name

    user = User(**payload, password=hash_password(user_in.password))
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise
    return user


def authenticate_user(db: Session, username_or_email: str, password: str) -> User:
    """Verify credentials (supports email or username login).

    Raises NotFoundException if credentials are invalid.
    """
    user = db.exec(
        select(User).where(
            (User.email == username_or_email) | (User.user_name == username_or_email)
        )
    ).first()

    if not user or not verify_password(password, user.password):
        raise InvalidInputException("Incorrect username/email or password")

    if user.user_status != UserStatus.active:
        raise InvalidInputException("Inactive user")

    return user


def update_user(db: Session, user: User, user_in: UserUpdate) -> User:
    """Update a user's fields. Handles password hashing if provided."""
    update_data = user_in.model_dump(exclude_unset=True)

    if "password" in update_data and update_data.get("password"):
        update_data["password"] = hash_password(update_data["password"])

    for field, value in update_data.items():
        setattr(user, field, value)

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user_by_id(db: Session, user_id: int, user_in: UserUpdate) -> User:
    """Update user by ID with uniqueness checks for email/username."""
    user = get_user_by_id(db, user_id)
    if not user:
        raise NotFoundException("User")

    update_data = user_in.model_dump(exclude_unset=True)

    if "email" in update_data and update_data["email"]:
        existing = db.exec(
            select(User).where(User.email == update_data["email"], User.user_id != user_id)
        ).first()
        if existing:
            raise AlreadyExistsException("Email already in use")

    if "user_name" in update_data and update_data["user_name"]:
        existing = db.exec(
            select(User).where(User.user_name == update_data["user_name"], User.user_id != user_id)
        ).first()
        if existing:
            raise AlreadyExistsException("Username already in use")

    if "password" in update_data and update_data.get("password"):
        update_data["password"] = hash_password(update_data["password"])

    for field, value in update_data.items():
        setattr(user, field, value)

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: int) -> None:
    """Delete a user and clean up related data."""
    user = get_user_by_id(db, user_id)
    if not user:
        raise NotFoundException("User")

    db.execute(text("UPDATE classes SET teacher_id = NULL WHERE teacher_id = :uid"), {"uid": user_id})
    db.execute(text("DELETE FROM user_class WHERE user_id = :uid"), {"uid": user_id})
    db.execute(text("DELETE FROM results WHERE user_id = :uid"), {"uid": user_id})

    db.delete(user)
    db.commit()
    logger.info("Deleted user_id=%s and related data", user_id)
