"""Result endpoint: create result with permission checks."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.classes import Class
from app.models.exams import ClassExam
from app.models.user import User, UserClass, UserRole
from app.schemas.results import ResultCreate, ResultRead
from app.services import result_service

router = APIRouter()


@router.post("/", response_model=ResultRead, status_code=status.HTTP_201_CREATED)
def create_result(
    result_in: ResultCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Create a new result.

    Permissions:
      - Admin: can create any result
      - User: can create their own result
      - Teacher: can create results for students in their class
    """
    if current_user.user_role == UserRole.admin:
        permitted = True
    elif current_user.user_id == result_in.user_id:
        permitted = True
    else:
        permitted = False

    if not permitted and current_user.user_role == UserRole.teacher:
        stmt = (
            select(Class)
            .join(ClassExam, Class.class_id == ClassExam.class_id)
            .join(UserClass, UserClass.class_id == Class.class_id)
            .where(
                ClassExam.exam_id == result_in.exam_id,
                Class.teacher_id == current_user.user_id,
                UserClass.user_id == result_in.user_id,
            )
        )
        if db.exec(stmt).first():
            permitted = True

    if not permitted:
        raise HTTPException(status_code=403, detail="Not enough permissions to create this result")

    return result_service.create_result(db, result_in)
