from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User, UserRole
from app.models.exams import Exam
from app.models.result import Result
from app.models.classes import Class
from app.schemas.exams import ExamCreate, ExamRead, ExamUpdate, ResultCreate, ResultRead, ResultUpdate
from app.services import exam_service, result_service
from datetime import datetime


router = APIRouter()


@router.post("/", response_model=ExamRead)
def create_exam(
    exam_in: ExamCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Create a new exam"""
    # Verify class exists
    db_class = db.get(Class, exam_in.class_id)
    if not db_class:
        raise HTTPException(
            status_code=404,
            detail="Class not found"
        )

    # Only teachers of the class or admins can create exams
    if current_user.user_role not in [UserRole.admin, UserRole.teacher] and db_class.teacher_id != current_user.user_id:
        raise HTTPException(
            status_code=403,
            detail="Not enough permissions"
        )

    exam = exam_service.create_exam(db, exam_in)
    return exam


@router.get("/{exam_id}", response_model=ExamRead)
def get_exam(
    exam_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get exam by ID"""
    exam = exam_service.get_exam(db, exam_id)
    if not exam:
        raise HTTPException(
            status_code=404,
            detail="Exam not found"
        )
    return exam


@router.put("/{exam_id}", response_model=ExamRead)
def update_exam(
    exam_id: int,
    exam_in: ExamUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Update exam"""
    exam = exam_service.get_exam(db, exam_id)
    if not exam:
        raise HTTPException(
            status_code=404,
            detail="Exam not found"
        )

    db_class = db.get(Class, exam.class_id)
    if not db_class:
        raise HTTPException(
            status_code=404,
            detail="Class not found"
        )

    # Only teachers of the class or admins can update exams
    if current_user.user_role not in [UserRole.admin, UserRole.teacher] and db_class.teacher_id != current_user.user_id:
        raise HTTPException(
            status_code=403,
            detail="Not enough permissions"
        )

    exam = exam_service.update_exam(db, exam_id, exam_in)
    return exam


@router.delete("/{exam_id}")
def delete_exam(
    exam_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Delete exam"""
    exam = exam_service.get_exam(db, exam_id)
    if not exam:
        raise HTTPException(
            status_code=404,
            detail="Exam not found"
        )

    db_class = db.get(Class, exam.class_id)
    if not db_class:
        raise HTTPException(
            status_code=404,
            detail="Class not found"
        )

    # Only teachers of the class or admins can delete exams
    if current_user.user_role not in [UserRole.admin, UserRole.teacher] and db_class.teacher_id != current_user.user_id:
        raise HTTPException(
            status_code=403,
            detail="Not enough permissions"
        )

    exam_service.delete_exam(db, exam_id)
    return {"message": "Exam deleted successfully"}

# Result endpoints
@router.post("/{exam_id}/results", response_model=ResultRead)
def create_result(
    exam_id: int,
    result_in: ResultCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Submit exam result for a student"""
    # Verify exam exists
    exam = exam_service.get_exam(db, exam_id)
    if not exam:
        raise HTTPException(
            status_code=404,
            detail="Exam not found"
        )

    # Ensure the result is for this exam
    if result_in.exam_id != exam_id:
        raise HTTPException(
            status_code=400,
            detail="Exam ID mismatch"
        )

    result = result_service.create_result(db, result_in)
    return result


@router.get("/{exam_id}/results", response_model=List[ResultRead])
def list_exam_results(
    exam_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get all results for an exam"""
    exam = exam_service.get_exam(db, exam_id)
    if not exam:
        raise HTTPException(
            status_code=404,
            detail="Exam not found"
        )

    results = result_service.list_results(db, exam_id=exam_id)
    return results


@router.get("/results/{result_id}", response_model=ResultRead)
def get_result(
    result_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get a specific result by ID"""
    result = result_service.get_result(db, result_id)
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Result not found"
        )
    return result


@router.put("/results/{result_id}", response_model=ResultRead)
def update_result(
    result_id: int,
    result_in: ResultUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Update a result"""
    result = result_service.get_result(db, result_id)
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Result not found"
        )

    # Only teachers or admins can update results
    exam = exam_service.get_exam(db, result.exam_id)
    if not exam:
        raise HTTPException(
            status_code=404,
            detail="Exam not found"
        )

    db_class = db.get(Class, exam.class_id)
    if current_user.user_role not in [UserRole.admin, UserRole.teacher] and db_class.teacher_id != current_user.user_id:
        raise HTTPException(
            status_code=403,
            detail="Not enough permissions"
        )

    result = result_service.update_result(db, result_id, result_in)
    return result


@router.delete("/results/{result_id}")
def delete_result(
    result_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Delete a result"""
    result = result_service.get_result(db, result_id)
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Result not found"
        )

    # Only teachers or admins can delete results
    exam = exam_service.get_exam(db, result.exam_id)
    if not exam:
        raise HTTPException(
            status_code=404,
            detail="Exam not found"
        )

    db_class = db.get(Class, exam.class_id)
    if current_user.user_role not in [UserRole.admin, UserRole.teacher] and db_class.teacher_id != current_user.user_id:
        raise HTTPException(
            status_code=403,
            detail="Not enough permissions"
        )

    result_service.delete_result(db, result_id)
    return {"message": "Result deleted successfully"}