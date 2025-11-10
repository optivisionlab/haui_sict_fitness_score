from typing import List, Optional
from sqlmodel import Session, select
from fastapi import HTTPException, status
from datetime import datetime

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
    db.commit()
    db.refresh(result)
    return result


def update_result(db: Session, result_id: int, result_in: ResultUpdate) -> Result:
    result = get_result(db, result_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")
    
    data = result_in.dict(exclude_unset=True)
    for k, v in data.items():
        setattr(result, k, v)
    
    result.updated_at = datetime.utcnow()
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


def delete_result(db: Session, result_id: int) -> None:
    result = get_result(db, result_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")
    db.delete(result)
    db.commit()
