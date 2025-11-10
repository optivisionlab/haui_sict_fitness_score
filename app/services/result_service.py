from typing import List, Optional
from sqlmodel import Session, select
from fastapi import HTTPException, status
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from app.models.result import Result
from app.models.exams import Exam
from app.models.user import User
from app.schemas.exams import ResultCreate, ResultUpdate


def get_result(db: Session, result_id: int) -> Optional[Result]:
    return db.get(Result, result_id)


def get_results_by_user_exam(db: Session, user_id: int, exam_id: int) -> List[Result]:
    """Return all results for a given user and exam (multiple attempts / steps).

    Use this when you need the full history of attempts.
    """
    return db.exec(
        select(Result).where((Result.user_id == user_id) & (Result.exam_id == exam_id)).order_by(Result.step)
    ).all()


def get_result_by_user_exam_step(db: Session, user_id: int, exam_id: int, step: int) -> Optional[Result]:
    """Return a single result matching (user, exam, step) if present."""
    return db.exec(
        select(Result).where(
            (Result.user_id == user_id) & (Result.exam_id == exam_id) & (Result.step == step)
        )
    ).first()


def list_results(db: Session, exam_id: Optional[int] = None, user_id: Optional[int] = None, skip: int = 0, limit: int = 100) -> List[Result]:
    q = select(Result)
    if exam_id is not None:
        q = q.where(Result.exam_id == exam_id)
    if user_id is not None:
        q = q.where(Result.user_id == user_id)
    return db.exec(q.offset(skip).limit(limit)).all()


def create_result(db: Session, result_in: ResultCreate) -> Result:
    # Validate user exists
    user = db.get(User, result_in.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Validate exam exists
    exam = db.get(Exam, result_in.exam_id)
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
    
    # If a specific step is provided, ensure uniqueness on (user, exam, step).
    if result_in.step is not None:
        existing = get_result_by_user_exam_step(db, result_in.user_id, result_in.exam_id, result_in.step)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Result already exists for this user, exam and step",
            )
        result_data = result_in.dict()
    else:
        # Auto-assign step = max(existing steps) + 1 (or 1 if none exist)
        last = db.exec(
            select(Result).where((Result.user_id == result_in.user_id) & (Result.exam_id == result_in.exam_id)).order_by(Result.step.desc()).limit(1)
        ).first()
        next_step = 1 if not last or last.step is None else (last.step + 1)
        result_data = result_in.dict()
        result_data["step"] = next_step

    result = Result(**result_data)
    db.add(result)
    try:
        db.commit()
    except IntegrityError:
        # This should be rare because we checked uniqueness above, but
        # handle the DB-level uniqueness violation gracefully.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Result violates a database constraint (possibly duplicate user/exam/step).",
        )
    db.refresh(result)
    return result


def update_result(db: Session, result_id: int, result_in: ResultUpdate) -> Result:
    result = get_result(db, result_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")
    
    data = result_in.dict(exclude_unset=True)
    # If updating any of user_id, exam_id or step we must ensure the
    # uniqueness constraint (user_id, exam_id, step) is preserved.
    # Reject explicit nulls for non-nullable DB columns to avoid IntegrityError.
    for required_field in ("user_id", "exam_id", "step"):
        if required_field in data and data[required_field] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"'{required_field}' cannot be null",
            )

    new_user_id = data.get("user_id", result.user_id)
    new_exam_id = data.get("exam_id", result.exam_id)
    # If step is omitted, keep existing step; if provided, we already rejected None above
    new_step = data.get("step") if ("step" in data) else result.step

    # If any of these changed (or even if not), check for an existing row
    # with the same tuple but a different result_id.
    conflict = db.exec(
        select(Result).where(
            (Result.user_id == new_user_id)
            & (Result.exam_id == new_exam_id)
            & (Result.step == new_step)
            & (Result.result_id != result_id)
        )
    ).first()

    if conflict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Another result with the same user_id, exam_id and step already exists",
        )

    for k, v in data.items():
        setattr(result, k, v)

    result.updated_at = datetime.utcnow()
    db.add(result)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Result update violates a database constraint (possibly duplicate user/exam/step).",
        )
    db.refresh(result)
    return result


def delete_result(db: Session, result_id: int) -> None:
    result = get_result(db, result_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")
    db.delete(result)
    db.commit()
