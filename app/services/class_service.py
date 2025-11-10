from typing import Any, List, Optional
from sqlmodel import Session, select
from fastapi import HTTPException, status

from app.models.classes import Class, UserClass
from app.models.user import User

def get_class(db: Session, class_id: int) -> Optional[Class]:
    return db.get(Class, class_id)

def list_classes(db: Session, skip: int = 0, limit: int = 100) -> List[Class]:
    return db.exec(select(Class).offset(skip).limit(limit)).all()

def create_class(db: Session, class_in: dict) -> Class:
    db_class = Class(**class_in)
    db.add(db_class)
    db.commit()
    db.refresh(db_class)
    return db_class


def update_class(db: Session, class_id: int, data: dict) -> Class:
    db_class = get_class(db, class_id)
    if not db_class:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")
    for k, v in data.items():
        setattr(db_class, k, v)
    db.add(db_class)
    db.commit()
    db.refresh(db_class)
    return db_class


def delete_class(db: Session, class_id: int) -> None:
    db_class = get_class(db, class_id)
    if not db_class:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")
    db.delete(db_class)
    db.commit()


def enroll_user(db: Session, class_id: int, user_id: int) -> None:
    # check exist
    exists = db.exec(select(UserClass).where((UserClass.class_id == class_id) & (UserClass.user_id == user_id))).first()
    if exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already enrolled")
    user_class = UserClass(class_id=class_id, user_id=user_id)
    db.add(user_class)
    db.commit()

def get_students_in_class(db: Session, class_id: int) -> List[User]:
    stmt = select(User).join(UserClass).where(UserClass.class_id == class_id)
    return db.exec(stmt).all()