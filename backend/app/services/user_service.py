from typing import Optional, List
from sqlmodel import Session, select
from fastapi import HTTPException, status
from sqlalchemy import text

from app.models.user import User
from app.schemas.users import UserCreate, UserUpdate
from app.core.security import hash_password, verify_password

from app.models.user import User
from app.schemas.users import UserCreate, UserUpdate
from app.core.security import hash_password, verify_password


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.get(User, user_id)


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.exec(select(User).where(User.email == email)).first()


def get_user_by_username(db: Session, user_name: str) -> Optional[User]:
    return db.exec(select(User).where(User.user_name == user_name)).first()


def list_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    return db.exec(select(User).offset(skip).limit(limit)).all()


def create_user(db: Session, user_in: UserCreate) -> User:
    # uniqueness checks
    if get_user_by_email(db, user_in.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    if get_user_by_username(db, user_in.user_name):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")

    hashed = hash_password(user_in.password)
    db_user = User(**user_in.dict(exclude={"password"}), password=hashed)
    db.add(db_user)
    try:
        db.commit()
        db.refresh(db_user)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    return db_user


def update_user(db: Session, user_id: int, user_in: UserUpdate) -> User:
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    data = user_in.dict(exclude_unset=True)
    if "password" in data and data["password"]:
        data["password"] = hash_password(data["password"])

    for field, value in data.items():
        setattr(user, field, value)

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: int) -> None:
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    # Cleanup related data explicitly to keep behavior consistent across DBs.
    # 1) Set teacher_id = NULL for classes taught by this user
    db.execute(text("""
        UPDATE classes SET teacher_id = NULL WHERE teacher_id = :uid
        """), {"uid": user_id})
    # 2) Delete enrollments
    db.execute(text("""
        DELETE FROM user_class WHERE user_id = :uid
        """), {"uid": user_id})
    # 3) Delete results
    db.execute(text("""
        DELETE FROM results WHERE user_id = :uid
        """), {"uid": user_id})

    db.delete(user)
    db.commit()


def authenticate_user(db: Session, username_or_email: str, password: str) -> Optional[User]:
    # allow login by email or username
    user = db.exec(
        select(User).where((User.email == username_or_email) | (User.user_name == username_or_email))
    ).first()
    if not user:
        return None
    if not verify_password(password, user.password):
        return None
    return user
