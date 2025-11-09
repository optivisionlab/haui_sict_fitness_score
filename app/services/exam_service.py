from typing import Any, List, Optional
from sqlmodel import Session, select
from fastapi import HTTPException, status
from datetime import datetime

from app.models.exams import Exam
from app.models.classes import Class
from app.schemas.exams import ExamCreate, ExamUpdate


def get_exam(db: Session, exam_id: int) -> Optional[Exam]:
    return db.get(Exam, exam_id)


def list_exams(db: Session, class_id: Optional[int] = None, skip: int = 0, limit: int = 100) -> List[Exam]:
    q = select(Exam)
    if class_id is not None:
        q = q.where(Exam.class_id == class_id)
    return db.exec(q.offset(skip).limit(limit)).all()


def create_exam(db: Session, exam_in: ExamCreate) -> Exam:
    # validate class exists
    cls = db.get(Class, exam_in.class_id)
    if not cls:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")
    exam = Exam(**exam_in.dict())
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return exam


def update_exam(db: Session, exam_id: int, exam_in: ExamUpdate) -> Exam:
    exam = get_exam(db, exam_id)
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
    
    data = exam_in.dict(exclude_unset=True)
    for k, v in data.items():
        setattr(exam, k, v)
    
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return exam


def delete_exam(db: Session, exam_id: int) -> None:
    exam = get_exam(db, exam_id)
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
    db.delete(exam)
    db.commit()