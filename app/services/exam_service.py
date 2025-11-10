from typing import Any, List, Optional
from sqlmodel import Session, select
from fastapi import HTTPException, status
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text

from app.models.exams import Exam, ClassExam
from app.models.classes import Class
from app.schemas.exams import ExamCreate, ExamUpdate


def get_exam(db: Session, exam_id: int) -> Optional[Exam]:
    return db.get(Exam, exam_id)


def list_exams(db: Session, class_id: Optional[int] = None, skip: int = 0, limit: int = 100) -> List[Exam]:
    q = select(Exam)
    if class_id is not None:
        q = q.join(ClassExam, Exam.exam_id == ClassExam.exam_id).where(ClassExam.class_id == class_id)
    return db.exec(q.offset(skip).limit(limit)).all()


def create_exam(db: Session, exam_in: ExamCreate, class_id: Optional[int] = None) -> Exam:
    """Create an Exam row and optionally link it to a class via ClassExam.

    If `class_id` is provided the function validates the class exists
    and will attempt to create the ClassExam join row. Duplicate-link
    integrity errors are treated as idempotent for the create flow.
    """
    # Create exam row
    data = exam_in.dict()
    exam = Exam(**data)
    db.add(exam)
    db.commit()
    db.refresh(exam)

    # If a class_id was provided, create the join record
    if class_id is not None:
        cls = db.get(Class, class_id)
        if not cls:
            # remove created exam to avoid dangling row
            db.delete(exam)
            db.commit()
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")

        link = ClassExam(class_id=class_id, exam_id=exam.exam_id)
        db.add(link)
        try:
            db.commit()
        except IntegrityError:
            # idempotent: link already exists
            db.rollback()
    return exam


def add_exam_to_class(db: Session, exam_id: int, class_id: int) -> ClassExam:
    """Create a ClassExam link between an existing exam and class.

    Raises HTTPException if either resource is missing or the link exists.
    """
    exam = db.get(Exam, exam_id)
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

    cls = db.get(Class, class_id)
    if not cls:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")

    link = ClassExam(class_id=class_id, exam_id=exam_id)
    db.add(link)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Exam already linked to this class")
    return link


def remove_exam_from_class(db: Session, exam_id: int, class_id: int) -> None:
    """Remove a ClassExam link. Does not delete the exam itself.

    Raises 404 if the link does not exist.
    """
    row = db.exec(select(ClassExam).where((ClassExam.class_id == class_id) & (ClassExam.exam_id == exam_id))).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")
    db.delete(row)
    db.commit()


def update_exam(db: Session, exam_id: int, exam_in: ExamUpdate) -> Exam:
    exam = get_exam(db, exam_id)
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
    
    data = exam_in.dict(exclude_unset=True)
    for k, v in data.items():
        setattr(exam, k, v)
    # set updated timestamp
    exam.updated_at = datetime.utcnow()
    
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return exam


def delete_exam(db: Session, exam_id: int) -> None:
    exam = get_exam(db, exam_id)
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
    # Explicitly remove related rows to keep behavior predictable across
    # different DB setups (even though FKs usually cascade).
    try:
        # Delete results tied to this exam
        db.exec(text("DELETE FROM results WHERE exam_id = :eid"), params={"eid": exam_id})

        # Delete class links
        db.exec(text("DELETE FROM class_exam WHERE exam_id = :eid"), params={"eid": exam_id})
        # Finally delete the exam row
        db.delete(exam)
        db.commit()
    except Exception:
        db.rollback()
        raise