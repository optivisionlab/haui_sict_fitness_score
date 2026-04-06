"""Exam endpoints: CRUD + exam-scoped result operations."""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.classes import Class
from app.models.exams import ClassExam
from app.models.user import User, UserRole
from app.schemas.exams import ExamCreate, ExamRead, ExamUpdate
from app.schemas.results import ResultCreate, ResultRead, ResultUpdate
from app.services import exam_service, result_service

router = APIRouter()


def _get_linked_classes(db: Session, exam_id: int) -> list[Class]:
    """Fetch classes linked to an exam via ClassExam."""
    return db.exec(
        select(Class)
        .join(ClassExam, Class.class_id == ClassExam.class_id)
        .where(ClassExam.exam_id == exam_id)
    ).all()


def _check_exam_permission(current_user: User, linked_classes: list[Class], *, allow_student: bool = False) -> None:
    """Raise 403 if the user lacks permission for the exam's linked classes."""
    if current_user.user_role == UserRole.admin:
        return
    if current_user.user_role == UserRole.teacher:
        if any(c.teacher_id == current_user.user_id for c in linked_classes):
            return
    if allow_student:
        return
    raise HTTPException(status_code=403, detail="Not enough permissions")


# ---------------------------------------------------------------------------
# Exam CRUD
# ---------------------------------------------------------------------------


@router.get("/", response_model=list[ExamRead])
def list_exams(
    class_id: Optional[int] = Query(None, description="Optional class_id to filter exams"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> Any:
    return exam_service.list_exams(db, class_id=class_id, skip=skip, limit=limit)


@router.post("/", response_model=ExamRead)
def create_exam(
    exam_in: ExamCreate,
    class_id: Optional[int] = Query(None, description="Optional class_id to link the exam"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Create an exam. If class_id is provided, caller must be class teacher or admin."""
    if class_id is not None:
        db_class = db.get(Class, class_id)
        if not db_class:
            raise HTTPException(status_code=404, detail="Class not found")
        if current_user.user_role != UserRole.admin and db_class.teacher_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Not enough permissions")
    else:
        if current_user.user_role != UserRole.admin:
            raise HTTPException(status_code=403, detail="Not enough permissions")

    return exam_service.create_exam(db, exam_in, class_id=class_id)


@router.get("/{exam_id}", response_model=ExamRead)
def get_exam(exam_id: int, db: Session = Depends(get_db)) -> Any:
    exam = exam_service.get_exam(db, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    return exam


@router.put("/{exam_id}", response_model=ExamRead)
def update_exam(
    exam_id: int,
    exam_in: ExamUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    exam = exam_service.get_exam(db, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    linked_classes = _get_linked_classes(db, exam_id)
    if linked_classes:
        _check_exam_permission(current_user, linked_classes)
    elif current_user.user_role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    return exam_service.update_exam(db, exam_id, exam_in)


@router.delete("/{exam_id}")
def delete_exam(
    exam_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    exam = exam_service.get_exam(db, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    linked_classes = _get_linked_classes(db, exam_id)
    if linked_classes:
        _check_exam_permission(current_user, linked_classes)
    elif current_user.user_role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    exam_service.delete_exam(db, exam_id)
    return {"message": "Exam deleted successfully"}


# ---------------------------------------------------------------------------
# Exam-scoped result operations
# ---------------------------------------------------------------------------


@router.get("/{exam_id}/results", response_model=list[ResultRead])
def list_exam_results(
    exam_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    exam = exam_service.get_exam(db, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    linked_classes = _get_linked_classes(db, exam_id)
    if not linked_classes:
        raise HTTPException(status_code=404, detail="Class not found for this exam")
    _check_exam_permission(current_user, linked_classes)

    return result_service.list_results(db, exam_id=exam_id, skip=skip, limit=limit)


@router.post("/{exam_id}/results", response_model=ResultRead)
def create_exam_result(
    exam_id: int,
    result_in: ResultCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    exam = exam_service.get_exam(db, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    linked_classes = _get_linked_classes(db, exam_id)
    if not linked_classes:
        raise HTTPException(status_code=404, detail="Class not found for this exam")

    if current_user.user_role == UserRole.admin:
        pass
    elif current_user.user_role == UserRole.teacher:
        if not any(c.teacher_id == current_user.user_id for c in linked_classes):
            raise HTTPException(status_code=403, detail="Not enough permissions")
    elif current_user.user_id != result_in.user_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    if result_in.exam_id != exam_id:
        raise HTTPException(status_code=400, detail="exam_id in body must match path")

    return result_service.create_result(db, result_in)


@router.get("/{exam_id}/results/{result_id}", response_model=ResultRead)
def get_result(
    exam_id: int,
    result_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    result = result_service.get_result(db, result_id)
    if not result or result.exam_id != exam_id:
        raise HTTPException(status_code=404, detail="Result not found")

    linked_classes = _get_linked_classes(db, exam_id)
    if not linked_classes:
        raise HTTPException(status_code=404, detail="Class not found for this exam")

    if current_user.user_role == UserRole.admin:
        pass
    elif current_user.user_role == UserRole.teacher:
        if not any(c.teacher_id == current_user.user_id for c in linked_classes):
            raise HTTPException(status_code=403, detail="Not enough permissions")
    elif current_user.user_id != result.user_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    return result


@router.put("/{exam_id}/results/{result_id}", response_model=ResultRead)
def update_result(
    exam_id: int,
    result_id: int,
    result_in: ResultUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    result = result_service.get_result(db, result_id)
    if not result or result.exam_id != exam_id:
        raise HTTPException(status_code=404, detail="Result not found")

    linked_classes = _get_linked_classes(db, exam_id)
    if not linked_classes:
        raise HTTPException(status_code=404, detail="Class not found for this exam")
    _check_exam_permission(current_user, linked_classes)

    return result_service.update_result(db, result_id, result_in)


@router.delete("/{exam_id}/results/{result_id}")
def delete_result(
    exam_id: int,
    result_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    result = result_service.get_result(db, result_id)
    if not result or result.exam_id != exam_id:
        raise HTTPException(status_code=404, detail="Result not found")

    linked_classes = _get_linked_classes(db, exam_id)
    if not linked_classes:
        raise HTTPException(status_code=404, detail="Class not found for this exam")
    _check_exam_permission(current_user, linked_classes)

    result_service.delete_result(db, result_id)
    return {"message": "Result deleted successfully"}
