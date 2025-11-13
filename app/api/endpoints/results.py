from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User, UserRole
from app.models.classes import Class, UserClass
from app.models.exams import ClassExam
from app.schemas.exams import ResultCreate, ResultRead
from app.services import result_service

router = APIRouter()


@router.post("/", response_model=ResultRead, status_code=status.HTTP_201_CREATED)
def create_result(
    result_in: ResultCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Create a new Result row.

    Permissions:
      - admin users can create any result
      - users can create their own result (result.user_id == current_user.user_id)
      - teachers can create results for students in their class for exams linked to that class
    """
    # Quick permission checks
    if current_user.user_role == UserRole.admin:
        permitted = True
    elif current_user.user_id == result_in.user_id:
        permitted = True
    else:
        permitted = False

    # If the caller is a teacher, check that teacher teaches a class that links to
    # the exam and that the target user is enrolled in that class.
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
        linked = db.exec(stmt).first()
        if linked:
            permitted = True

    if not permitted:
        raise HTTPException(status_code=403, detail="Not enough permissions to create this result")

    # Delegate to service which performs validation and uniqueness checks
    created = result_service.create_result(db, result_in)
    return created
