from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from sqlalchemy import text
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User, UserRole, UserStatus
from app.models.classes import Class, UserClass
from app.models.exams import Exam, ClassExam
from app.models.result import Result
from app.schemas.classes import ClassCreate, ClassRead, ClassUpdate
from app.schemas.exams import ExamCreate, ExamRead
from app.services.result_service import compute_avg_speed
from app.services import exam_service
import httpx
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from loguru import logger
from sqlalchemy.sql import and_
from fastapi import Body
from pydantic import BaseModel, Field
from app.services import exam_service
import httpx


router = APIRouter()


@router.post("/", response_model=ClassRead)
def create_class(
    class_in: ClassCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Create new class.
    """
    if current_user.user_role != UserRole.admin:
        raise HTTPException(
            status_code=403,
            detail="Not enough permissions"
        )
    # If a teacher_id is provided, ensure that user exists and has an appropriate role
    teacher_id = getattr(class_in, "teacher_id", None)
    if teacher_id is not None:
        teacher = db.get(User, teacher_id)
        if not teacher:
            raise HTTPException(status_code=400, detail="teacher_id does not exist")
        if teacher.user_role not in [UserRole.teacher, UserRole.admin]:
            raise HTTPException(status_code=400, detail="Assigned teacher must have role 'teacher' or 'admin'")

    db_class = Class(**class_in.dict())
    db.add(db_class)
    db.commit()
    db.refresh(db_class)
    return db_class


@router.get("/", response_model=List[ClassRead])
def list_classes(
    skip: int = 0,
    limit: int = 100,
    teacher_id: Optional[int] = None,
    student_id: Optional[int] = None,
    course_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    List classes with flexible filtering rules:
    - Admin: can view all classes and filter by teacher_id, student_id, course_type in any combination.
    - Teacher: can view classes they teach; may filter by course_type.
    - Student: can view classes they are enrolled in.
    """
    # Admin: build query supporting combinations of teacher_id, student_id, course_type
    if current_user.user_role == UserRole.admin:
        # Start from Class
        q = select(Class)

        # If filtering by student_id, join the user_class table
        if student_id is not None:
            q = q.join(UserClass, Class.class_id == UserClass.class_id).where(UserClass.user_id == student_id)

        # Apply teacher filter if provided
        if teacher_id is not None:
            q = q.where(Class.teacher_id == teacher_id)

        # Apply course_type filter if provided
        if course_type:
            q = q.where(Class.course_type == course_type)

        classes = db.exec(q.offset(skip).limit(limit)).all()
        return classes

    # Teacher: classes they teach, optional course_type filter
    if current_user.user_role == UserRole.teacher:
        q = select(Class).where(Class.teacher_id == current_user.user_id)
        if course_type:
            q = q.where(Class.course_type == course_type)
        classes = db.exec(q.offset(skip).limit(limit)).all()
        return classes

    # Student (or other roles): classes the current user is enrolled in
    q = (
        select(Class)
        .join(UserClass, Class.class_id == UserClass.class_id)
        .where(UserClass.user_id == current_user.user_id)
    )
    if course_type:
        q = q.where(Class.course_type == course_type)
    classes = db.exec(q.offset(skip).limit(limit)).all()
    return classes


@router.get("/{class_id}", response_model=ClassRead)
def read_class(
    class_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get class by ID.
    """
    db_class = db.get(Class, class_id)
    if not db_class:
        raise HTTPException(
            status_code=404,
            detail="Class not found"
        )
    if current_user.user_role not in [UserRole.admin, UserRole.teacher]:
        raise HTTPException(
            status_code=403,
            detail="Not enough permissions"
        )
    return db_class


@router.put("/{class_id}", response_model=ClassRead)
def update_class(
    class_id: int,
    class_in: ClassUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Update class.
    """
    db_class = db.get(Class, class_id)
    if not db_class:
        raise HTTPException(
            status_code=404,
            detail="Class not found"
        )
    
    if current_user.user_role not in [UserRole.admin]:
        raise HTTPException(
            status_code=403,
            detail="Not enough permissions"
        )
    
    # If teacher_id is being updated, validate that the provided teacher exists
    # and has an appropriate role (teacher or admin). This mirrors the checks
    # performed in create_class and ensures related data remains consistent.
    update_data = class_in.dict(exclude_unset=True)
    if "teacher_id" in update_data:
        new_teacher_id = update_data.get("teacher_id")
        if new_teacher_id is not None:
            teacher = db.get(User, new_teacher_id)
            if not teacher:
                raise HTTPException(status_code=400, detail="teacher_id does not exist")
            if teacher.user_role not in [UserRole.teacher, UserRole.admin]:
                raise HTTPException(status_code=400, detail="Assigned teacher must have role 'teacher' or 'admin'")

    for field, value in update_data.items():
        setattr(db_class, field, value)
    
    db.add(db_class)
    db.commit()
    db.refresh(db_class)
    return db_class


@router.delete("/{class_id}")
def delete_class(
    class_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Delete class.
    """
    db_class = db.get(Class, class_id)
    if not db_class:
        raise HTTPException(
            status_code=404,
            detail="Class not found"
        )
    
    if current_user.user_role not in [UserRole.admin]:
        raise HTTPException(
            status_code=403,
            detail="Not enough permissions"
        )
    
    # Perform controlled cleanup of related rows to ensure application-level
    # consistency even if the database schema changes. The database has
    # cascading FKs, but doing this here keeps behavior explicit and
    # transactional from the API perspective.

    try:
        # Delete enrollments
        db.exec(text("DELETE FROM user_class WHERE class_id = :cid"), {"cid": class_id})

        # Collect exam_ids linked to this class before removing links
        rows = db.exec(text("SELECT exam_id FROM class_exam WHERE class_id = :cid"), {"cid": class_id}).all()
        exam_ids = [r[0] if isinstance(r, tuple) else getattr(r, 'exam_id', None) for r in rows]

        # Delete results for those exams (if any)
        if exam_ids:
            params = {f"id{i}": eid for i, eid in enumerate(exam_ids)}
            in_clause = ",".join(f":id{i}" for i in range(len(exam_ids)))
            db.exec(text(f"DELETE FROM results WHERE exam_id IN ({in_clause})"), params)

        # Delete class-exam links for this class
        db.exec(text("DELETE FROM class_exam WHERE class_id = :cid"), {"cid": class_id})

        # Delete exams that became orphaned (no remaining class links)
        if exam_ids:
            params = {f"id{i}": eid for i, eid in enumerate(exam_ids)}
            in_clause = ",".join(f":id{i}" for i in range(len(exam_ids)))
            db.exec(text(f"DELETE FROM exams WHERE exam_id IN ({in_clause}) AND NOT EXISTS (SELECT 1 FROM class_exam ce WHERE ce.exam_id = exams.exam_id)"), params)

        # Finally delete the class itself
        db.delete(db_class)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete class and related data")

    return {"message": "Class deleted successfully"}


@router.get("/{class_id}/user/{user_id}/results")
def get_user_results_in_class(
    class_id: int,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Return a user's results for exams in the given class, including basic user info.
    Access: admin, class teacher, or the user themself.
    """
    db_class = db.get(Class, class_id)
    if not db_class:
        raise HTTPException(status_code=404, detail="Class not found")

    # Permission check: admin, teacher of class, or the user themself
    if not (
        current_user.user_role == UserRole.admin
        or db_class.teacher_id == current_user.user_id
        or current_user.user_id == user_id
    ):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Optimized query:
    # - select Exam and Result in a single joined query
    # - filter by class via the join table `class_exam` and by user_id
    # - support pagination (skip/limit) and order by most recent results
    q = (
        select(Exam, Result, ClassExam)
        .join(ClassExam, Exam.exam_id == ClassExam.exam_id)
        .join(Result, Result.exam_id == Exam.exam_id)
        .where(ClassExam.class_id == class_id, Result.user_id == user_id)
        .order_by(Result.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    rows = db.exec(q).all()
    logger.info(f"rows: {rows}")
    logger.info("row") 
    # rows will be list of tuples (Exam, Result, ClassExam)
    results = []
    for exam, res, ce in rows:
        if res:
            results.append({
                "result_id": getattr(res, "result_id", None),
                "exam_id": getattr(res, "exam_id", None),
                "step": getattr(res, "step", None),
                "lap": getattr(res, "lap", None),
                "start_time": getattr(res, "start_time", None),
                "end_time": getattr(res, "end_time", None),
                "avg_speed": compute_avg_speed(getattr(res, "start_time", None), getattr(res, "end_time", None), getattr(res, "lap", 1)),
                "created_at": getattr(res, "created_at", None),
            })
        else:
            results.append({
                "result_id": None,
                "exam_id": getattr(ce, "exam_id", None),
                "exam_title": getattr(exam, "title", None),
                "exam_description": getattr(exam, "description", None),
                "exam_date": getattr(ce, "exam_date", None),
                "step": None,
                "lap": None,
                "start_time": None,
                "end_time": None,
                "avg_speed": None,
                "created_at": None,
            })

    user_info = {
        "user_id": user.user_id,
        "user_name": user.user_name,
        "full_name": user.full_name,
        "email": user.email,
        "phone_number": user.phone_number,
        "user_code": user.user_code,
    }

    return {"user": user_info, "results": results}

@router.get("/{class_id}/user/{user_id}/exams/results/top")
def get_user_exams_results_in_class(
    class_id: int,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:

    """Return the user's best results for each exam in a class (exam-level).
    Access: admin, class teacher, or that same user.
    """

    # --- Validate class ---
    db_class = db.get(Class, class_id)
    if not db_class:
        raise HTTPException(status_code=404, detail="Class not found")

    # --- Permission check ---
    if not (
        current_user.user_role == UserRole.admin
        or db_class.teacher_id == current_user.user_id
        or current_user.user_id == user_id
    ):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # --- Validate user ---
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # --- Query: get all exams in this class + their results (if any) for this user ---
    q = (
    select(Exam, Result, ClassExam)
    .join(ClassExam, Exam.exam_id == ClassExam.exam_id)
    .outerjoin(
        Result,
        and_(
            Result.exam_id == Exam.exam_id,
            Result.user_id == user_id
        )
    )
    .where(ClassExam.class_id == class_id)
    .order_by(Result.created_at.desc().nullslast())
    .offset(skip)
    .limit(limit)
)

    rows = db.exec(q).all()

    # --- Pick best result per exam ---
    best_by_exam = {}

    for exam, res, ce in rows:

        exam_id = exam.exam_id

        # Compute speed if result exists
        if res:
            lap_val = res.lap or 1
            speed_val = compute_avg_speed(res.start_time, res.end_time, lap_val)
            speed_val = speed_val if speed_val is not None else -1.0
        else:
            speed_val = -1.0

        cur = best_by_exam.get(exam_id)

        if cur is None:
            best_by_exam[exam_id] = {
                "exam": exam,
                "class_exam": ce,
                "result": res,
                "speed": speed_val,
            }
        else:
            # Compare speed
            if speed_val > cur["speed"]:
                best_by_exam[exam_id] = {
                    "exam": exam,
                    "class_exam": ce,
                    "result": res,
                    "speed": speed_val,
                }
            elif speed_val == cur["speed"] and res:
                # Tie-breaker: newest created_at
                prev = cur["result"]
                prev_ct = getattr(prev, "created_at", None)
                cur_ct = getattr(res, "created_at", None)

                if prev_ct is None or (cur_ct and cur_ct > prev_ct):
                    best_by_exam[exam_id] = {
                        "exam": exam,
                        "class_exam": ce,
                        "result": res,
                        "speed": speed_val,
                    }

    # --- Build output ---
    out = []
    for exam_id, info in best_by_exam.items():
        exam = info["exam"]
        ce = info["class_exam"]
        res = info["result"]

        if res:
            out.append({
                "result_id": res.result_id,
                "exam_id": ce.exam_id,
                "exam_title": exam.title,
                "exam_description": exam.description,
                "exam_date": ce.exam_date,
                "step": res.step,
                "lap": res.lap,
                "start_time": res.start_time,
                "end_time": res.end_time,
                "avg_speed": compute_avg_speed(res.start_time, res.end_time, res.lap),
                "created_at": res.created_at,
            })
        else:
            out.append({
                "result_id": None,
                "exam_id": ce.exam_id,
                "exam_title": exam.title,
                "exam_description": exam.description,
                "exam_date": ce.exam_date,
                "step": None,
                "lap": None,
                "start_time": None,
                "end_time": None,
                "avg_speed": None,
                "created_at": None,
            })

    return {
        "user": {
            "user_id": user.user_id,
            "user_name": user.user_name,
            "full_name": user.full_name,
            "email": user.email,
            "phone_number": user.phone_number,
            "user_code": user.user_code,
        },
        "results": out
    }

@router.get("/{class_id}/user/{user_id}/exam/{exam_id}/results")
def get_user_exam_result_in_class(
    class_id: int,
    user_id: int,
    exam_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Return detailed result rows for a specific user/exam/class matching the SQL example.

    Returns rows with fields:
    result_id, user_id, full_name, exam_id, exam_title, class_id, class_name,
    step, score, start_time, end_time, created_at
    """
    # Validate class exists
    db_class = db.get(Class, class_id)
    if not db_class:
        raise HTTPException(status_code=404, detail="Class not found")

    # Permission check: admin, teacher of class, or the user themself
    if not (
        current_user.user_role == UserRole.admin
        or db_class.teacher_id == current_user.user_id
        or current_user.user_id == user_id
    ):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Validate user exists
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate exam exists
    exam = db.get(Exam, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    # Query matching the provided SQL, join tables and filter
    q = (
        select(Result, Exam, Class, User)
        .join(Exam, Result.exam_id == Exam.exam_id)
        .join(ClassExam, Exam.exam_id == ClassExam.exam_id)
        .join(Class, ClassExam.class_id == Class.class_id)
        .join(User, Result.user_id == User.user_id)
        .where(Result.user_id == user_id, Class.class_id == class_id, Exam.exam_id == exam_id)
    )

    rows = db.exec(q).all()

    out = []
    for res, ex, cl, us in rows:
        out.append({
            "result_id": getattr(res, "result_id", None),
            "user_id": getattr(res, "user_id", None),
            "full_name": getattr(us, "full_name", None),
            "exam_id": getattr(res, "exam_id", None),
            "exam_title": getattr(ex, "title", None),
            "class_id": getattr(cl, "class_id", None),
            "class_name": getattr(cl, "class_name", None),
            "step": getattr(res, "step", None),
            "lap": getattr(res, "lap", None),
            "start_time": getattr(res, "start_time", None),
            "end_time": getattr(res, "end_time", None),
            "avg_speed": compute_avg_speed(getattr(res, "start_time", None), getattr(res, "end_time", None), getattr(res, "lap", 1)),
            "created_at": getattr(res, "created_at", None),
        })

    return {"rows": out}


@router.get("/{class_id}/exam/{exam_id}/results")
def get_class_exam_results(
    class_id: int,
    exam_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Return all results for a specific exam within a class.

    Access: admin or the class teacher.
    Supports pagination via skip/limit.
    """
    # Validate class and exam
    db_class = db.get(Class, class_id)
    if not db_class:
        raise HTTPException(status_code=404, detail="Class not found")

    exam = db.get(Exam, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    # Permission: only admin or the class teacher can fetch full class results
    if not (current_user.user_role == UserRole.admin or db_class.teacher_id == current_user.user_id):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Query results joined to users, ensure exam is linked to the class via class_exam
    # Join directly from results -> class_exam using Result.exam_id so we
    # don't rely on a `result.exam` attribute on the Result instance.
    q = (
        select(Result, User)
        .join(ClassExam, Result.exam_id == ClassExam.exam_id)
        .join(User, Result.user_id == User.user_id)
    .where(ClassExam.class_id == class_id, Result.exam_id == exam_id)
    # `Result.score` does not exist on the Result model. Order by
    # most-recent results instead (created_at). If you want to sort by
    # score, add a `score` column to the `Result` model and DB.
    .order_by(Result.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    rows = db.exec(q).all()

    out = []
    for res, us in rows:
        out.append({
            "result_id": getattr(res, "result_id", None),
            "user_id": getattr(res, "user_id", None),
            "full_name": getattr(us, "full_name", None),
            "exam_id": getattr(res, "exam_id", None),
            "step": getattr(res, "step", None),
            "lap": getattr(res, "lap", None),
            "start_time": getattr(res, "start_time", None),
            "end_time": getattr(res, "end_time", None),
            "avg_speed": compute_avg_speed(getattr(res, "start_time", None), getattr(res, "end_time", None), getattr(res, "lap", 1)),
            "created_at": getattr(res, "created_at", None),
        })

    return {"rows": out, "count": len(out)}


@router.get("/{class_id}/exam/{exam_id}/results/by-user")
def get_class_exam_results_grouped_by_user(
    class_id: int,
    exam_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Return exam results for the class grouped per user.

    For each user enrolled in the class, return user info and a list of
    results for the specified exam (may be empty if user hasn't submitted).
    Access: admin or the class teacher.
    """
    # Validate class and exam
    db_class = db.get(Class, class_id)
    if not db_class:
        raise HTTPException(status_code=404, detail="Class not found")

    exam = db.get(Exam, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    # Ensure exam is linked to this class
    linked = db.exec(select(ClassExam).where((ClassExam.class_id == class_id) & (ClassExam.exam_id == exam_id))).first()
    if not linked:
        raise HTTPException(status_code=404, detail="Exam is not linked to this class")

    # Permission: only admin or the class teacher
    if not (current_user.user_role == UserRole.admin or db_class.teacher_id == current_user.user_id):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Query users enrolled in class left-joined with results for the exam
    stmt = (
        select(User, Result)
        .join(UserClass, User.user_id == UserClass.user_id)
        .outerjoin(Result, (Result.user_id == User.user_id) & (Result.exam_id == exam_id))
        .where(UserClass.class_id == class_id)
        .order_by(User.full_name)
        .offset(skip)
        .limit(limit)
    )

    rows = db.exec(stmt).all()

    grouped = {}
    for user_obj, res in rows:
        uid = user_obj.user_id
        if uid not in grouped:
            grouped[uid] = {
                "user": {
                    "user_id": user_obj.user_id,
                    "user_name": user_obj.user_name,
                    "full_name": user_obj.full_name,
                    "email": user_obj.email,
                    "phone_number": user_obj.phone_number,
                    "user_code": user_obj.user_code,
                },
                "results": []
            }
        if res is not None:
            grouped[uid]["results"].append({
                "result_id": getattr(res, "result_id", None),
                "exam_id": getattr(res, "exam_id", None),
                "step": getattr(res, "step", None),
                "lap": getattr(res, "lap", None),
                "start_time": getattr(res, "start_time", None),
                "end_time": getattr(res, "end_time", None),
                "avg_speed": compute_avg_speed(getattr(res, "start_time", None), getattr(res, "end_time", None), getattr(res, "lap", 1)),
                "created_at": getattr(res, "created_at", None),
            })

    # Convert grouped dict to list
    out = list(grouped.values())
    return {"count": len(out), "items": out}


@router.get("/{class_id}/exam/{exam_id}/results/by-user/top")
def get_class_exam_top_result_by_user(
    class_id: int,
    exam_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Return, for each enrolled user in the class, the single result with the highest avg_speed
    for the specified exam. Access: admin or the class teacher.
    """
    # Validate class and exam
    db_class = db.get(Class, class_id)
    if not db_class:
        raise HTTPException(status_code=404, detail="Class not found")

    exam = db.get(Exam, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    # Ensure exam is linked to this class
    linked = db.exec(select(ClassExam).where((ClassExam.class_id == class_id) & (ClassExam.exam_id == exam_id))).first()
    if not linked:
        raise HTTPException(status_code=404, detail="Exam is not linked to this class")

    # Permission: only admin or the class teacher
    if not (current_user.user_role == UserRole.admin or db_class.teacher_id == current_user.user_id):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Query users enrolled in class left-joined with results for the exam
    stmt = (
        select(User, Result)
        .join(UserClass, User.user_id == UserClass.user_id)
        .outerjoin(Result, (Result.user_id == User.user_id) & (Result.exam_id == exam_id))
        .where(UserClass.class_id == class_id)
        .order_by(User.full_name)
        .offset(skip)
        .limit(limit)
    )

    rows = db.exec(stmt).all()

    # For each user pick the result with highest avg_speed (tie-breaker: latest created_at)
    grouped = {}
    for user_obj, res in rows:
        uid = user_obj.user_id
        if uid not in grouped:
            grouped[uid] = {
                "user": {
                    "user_id": user_obj.user_id,
                    "user_name": user_obj.user_name,
                    "full_name": user_obj.full_name,
                    "email": user_obj.email,
                    "phone_number": user_obj.phone_number,
                    "user_code": user_obj.user_code,
                },
                "top_result": None,
                "_top_speed": None,
            }

        if res is None:
            continue

        speed = compute_avg_speed(getattr(res, "start_time", None), getattr(res, "end_time", None), getattr(res, "lap", 1))
        # treat missing speed as -1 so any valid speed beats it
        speed_val = speed if speed is not None else -1.0

        current_best = grouped[uid]["_top_speed"]
        if current_best is None or speed_val > current_best:
            grouped[uid]["_top_result"] = res
            grouped[uid]["_top_speed"] = speed_val
        elif speed_val == current_best:
            # tie-breaker: prefer the more recent created_at
            prev = grouped[uid].get("_top_result")
            try:
                prev_ct = getattr(prev, "created_at", None)
                cur_ct = getattr(res, "created_at", None)
                if prev_ct is None or (cur_ct is not None and cur_ct > prev_ct):
                    grouped[uid]["_top_result"] = res
            except Exception:
                pass

    out = []
    for uid, info in grouped.items():
        top = info.get("_top_result")
        if top is None:
            out.append({"user": info["user"], "result": None})
        else:
            out.append({
                "user": info["user"],
                "result": {
                    "result_id": getattr(top, "result_id", None),
                    "exam_id": getattr(top, "exam_id", None),
                    "step": getattr(top, "step", None),
                    "lap": getattr(top, "lap", None),
                    "start_time": getattr(top, "start_time", None),
                    "end_time": getattr(top, "end_time", None),
                    "avg_speed": compute_avg_speed(getattr(top, "start_time", None), getattr(top, "end_time", None), getattr(top, "lap", 1)),
                    "created_at": getattr(top, "created_at", None),
                }
            })

    return {"count": len(out), "items": out}


@router.get("/{class_id}/exams/results/by-user")
def get_selected_exams_results_by_user(
    class_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Return results for exams with ids [1,2,3] for all users in the class.

    For each enrolled user return user info and a list of results for the
    selected exams (may be empty). Access: admin or the class teacher.
    """
    # Validate class
    db_class = db.get(Class, class_id)
    if not db_class:
        raise HTTPException(status_code=404, detail="Class not found")

    # Permission: admin or the class teacher can view all users' results.
    # A regular enrolled user may call this endpoint but will only receive their own data.
    view_all = False
    if current_user.user_role == UserRole.admin or db_class.teacher_id == current_user.user_id:
        view_all = True
    else:
        # ensure the caller is enrolled in the class before allowing access to their own data
        enrolled = db.exec(select(UserClass).where((UserClass.class_id == class_id) & (UserClass.user_id == current_user.user_id))).first()
        if not enrolled:
            raise HTTPException(status_code=403, detail="Not enough permissions")

    # Fixed set of exam IDs requested by the user story
    requested_exam_ids = [1, 2, 3]

    # Determine which of the requested exams are linked to this class
    rows = db.exec(select(ClassExam.exam_id).where((ClassExam.class_id == class_id) & (ClassExam.exam_id.in_(requested_exam_ids)))).all()
    linked_ids = [r[0] if isinstance(r, tuple) else r for r in rows]
    if not linked_ids:
        # none of the requested exams are linked to this class
        raise HTTPException(status_code=404, detail="Requested exams are not linked to this class")

    # Query users enrolled in class left-joined with results for the selected exams
    stmt = (
        select(User, Result, Exam, ClassExam)
        .join(UserClass, User.user_id == UserClass.user_id)
        .outerjoin(Result, (Result.user_id == User.user_id) & (Result.exam_id.in_(linked_ids)))
        .outerjoin(Exam, Result.exam_id == Exam.exam_id)
        .outerjoin(ClassExam, (ClassExam.exam_id == Exam.exam_id) & (ClassExam.class_id == class_id))
        .where(UserClass.class_id == class_id)
    )

    # If the caller is not allowed to view all, restrict to their own enrollment
    if not view_all:
        stmt = stmt.where(UserClass.user_id == current_user.user_id)

    stmt = stmt.order_by(User.full_name).offset(skip).limit(limit)

    rows = db.exec(stmt).all()

    grouped = {}
    for user_obj, res, ex, ce in rows:
        uid = user_obj.user_id
        if uid not in grouped:
            grouped[uid] = {
                "user": {
                    "user_id": user_obj.user_id,
                    "user_name": user_obj.user_name,
                    "full_name": user_obj.full_name,
                    "email": user_obj.email,
                    "phone_number": user_obj.phone_number,
                    "user_code": user_obj.user_code,
                },
                "results": []
            }
        if res is not None:
            grouped[uid]["results"].append({
                "result_id": getattr(res, "result_id", None),
                "exam_id": getattr(res, "exam_id", None),
                "exam_title": getattr(ex, "title", None),
                "exam_date": getattr(ce, "exam_date", None),
                "step": getattr(res, "step", None),
                "lap": getattr(res, "lap", None),
                "start_time": getattr(res, "start_time", None),
                "end_time": getattr(res, "end_time", None),
                "avg_speed": compute_avg_speed(getattr(res, "start_time", None), getattr(res, "end_time", None), getattr(res, "lap", 1)),
                "created_at": getattr(res, "created_at", None),
            })

    out = list(grouped.values())
    return {"count": len(out), "items": out}


@router.post("/{class_id}/enroll/{user_id}")
def enroll_student(
    class_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Enroll a student in a class.

    Validations performed:
    - class exists
    - user exists and has role 'student' and is active
    - class is active (business rule)
    - caller is admin or the class teacher
    - student isn't already enrolled (handles race with DB unique constraint)
    """
    # Ensure class exists
    db_class = db.get(Class, class_id)
    if not db_class:
        raise HTTPException(status_code=404, detail="Class not found")

    # Ensure the user exists
    student = db.get(User, user_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Ensure the user has the student role
    if student.user_role != UserRole.student:
        raise HTTPException(status_code=400, detail="User is not a student and cannot be enrolled")

    # Ensure the user is active
    if getattr(student, "user_status", None) != UserStatus.active:
        raise HTTPException(status_code=400, detail="Student is not active and cannot be enrolled")

    # Optional: ensure class is active
    if getattr(db_class, "class_status", None) and db_class.class_status != "active":
        raise HTTPException(status_code=400, detail="Cannot enroll into a non-active class")

    # Permission: admin or the class's teacher can enroll students
    if not (current_user.user_role == UserRole.admin):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Check duplicate enrollment
    enrollment = db.exec(
        select(UserClass).where(
            (UserClass.class_id == class_id) & (UserClass.user_id == user_id)
        )
    ).first()
    if enrollment:
        raise HTTPException(status_code=400, detail="Student already enrolled in this class")

    # Create enrollment and handle race conditions
    user_class = UserClass(class_id=class_id, user_id=user_id)
    db.add(user_class)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Student already enrolled (concurrent request)")

    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"message": "Student enrolled successfully"})


@router.post("/{class_id}/add/{exam_id}")
def add_exam_to_class(
    class_id: int,
    exam_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Add an existing exam to a class by creating a ClassExam link.

    Behaviour mirrors `enroll_student`: validate class and exam existence,
    require admin or the class teacher, prevent duplicates, and handle
    concurrent requests via IntegrityError handling.
    """
    # Ensure class exists
    db_class = db.get(Class, class_id)
    if not db_class:
        raise HTTPException(status_code=404, detail="Class not found")

    # Ensure exam exists
    exam = db.get(Exam, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    # Optional: ensure class is active
    if getattr(db_class, "class_status", None) and db_class.class_status != "active":
        raise HTTPException(status_code=400, detail="Cannot enroll into a non-active class")


    # Permission: only admin or the class's teacher
    if current_user.user_role not in [UserRole.admin, UserRole.teacher] and db_class.teacher_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Optional: prevent adding an exam to a class if the exam already belongs
    # to a class via exam.class_id (business decision). We still allow linking
    # different classes via class_exam; skip this check unless desired.

    # Check duplicate link
    existing = db.exec(
        select(ClassExam).where(
            (ClassExam.class_id == class_id) & (ClassExam.exam_id == exam_id)
        )
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Exam already added to this class")

    # Create link and handle race conditions
    class_exam = ClassExam(class_id=class_id, exam_id=exam_id)
    db.add(class_exam)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Exam already added (concurrent request)")

    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"message": "Exam added successfully"})


@router.get("/{class_id}/exams")
def get_exams_for_class(
    class_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Return all exams linked to a class including the exam_date stored on the link (class_exam).

    Access: admin, class teacher, or any enrolled student.
    Returns JSON: {"count": int, "items": [ {exam_id, title, description, exam_date}, ... ] }
    """
    db_class = db.get(Class, class_id)
    if not db_class:
        raise HTTPException(status_code=404, detail="Class not found")

    # Permission: admin, teacher of class, or enrolled student
    if not (
        current_user.user_role == UserRole.admin
        or db_class.teacher_id == current_user.user_id
        or db.exec(select(UserClass).where((UserClass.class_id == class_id) & (UserClass.user_id == current_user.user_id))).first()
    ):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Query exams linked to this class and include the exam_date from ClassExam
    q = (
        select(Exam, ClassExam)
        .join(ClassExam, Exam.exam_id == ClassExam.exam_id)
        .where(ClassExam.class_id == class_id)
        .order_by(ClassExam.exam_date)
    )

    rows = db.exec(q).all()
    items = []
    for exam, ce in rows:
        items.append({
            "exam_id": getattr(exam, "exam_id", None),
            "title": getattr(exam, "title", None),
            "description": getattr(exam, "description", None),
            "exam_date": getattr(ce, "exam_date", None),
        })

    return {"count": len(items), "items": items}




class BatchUserPayload(BaseModel):
    # The external API expects string IDs in the example payload; accept them as strings
    user_id: str = Field(..., description="User identifier as string")
    exam_id: str = Field(..., description="Exam identifier as string")
    step: int = Field(..., ge=1, description="Step number (positive integer)")
    start_time: Optional[str] = Field(None, description="ISO datetime string for start action")
    end_time: Optional[str] = Field(None, description="ISO datetime string for end action")


@router.post("/{class_id}/exam/{exam_id}/user/{user_id}/{step}/{action}")
async def handle_exam_action(
    class_id: int,
    exam_id: int,
    user_id: int,
    step: int,
    action: str,
    payload: BatchUserPayload = Body(..., description="Payload containing user_id, exam_id and either start_time or end_time depending on action"),
    db: Session = Depends(get_db),
):
    """
    action: 'start' hoặc 'end'
    Forwards the payload to an external tracking API after validating the class->exam link.
    """
    if action not in ["start", "end"]:
        raise HTTPException(status_code=400, detail="Hành động không hợp lệ (chỉ cho phép: start hoặc end)")

    # Ensure required action-specific time exists
    if action == "start" and not payload.start_time:
        raise HTTPException(status_code=400, detail="Thiếu start_time trong payload")
    if action == "end" and not payload.end_time:
        raise HTTPException(status_code=400, detail="Thiếu end_time trong payload")

    user_record = {
        "user_id": str(payload.user_id),
        "exam_id": str(payload.exam_id),
        "step": int(payload.step),
    }
    if payload.start_time:
        user_record["start_time"] = payload.start_time
    if payload.end_time:
        user_record["end_time"] = payload.end_time

    batch_payload = {"users": [user_record]}

    # Validate class exists and exam is linked to this class
    db_class = db.get(Class, class_id)
    if not db_class:
        raise HTTPException(status_code=404, detail="Class not found")
    linked = db.exec(select(ClassExam).where((ClassExam.class_id == class_id) & (ClassExam.exam_id == exam_id))).first()
    if not linked:
        raise HTTPException(status_code=404, detail="Exam is not linked to the provided class_id")

    # forward to external API (batch format)
    external_api_url = "http://10.100.200.119:8001/track_batch"
    try:
        async with httpx.AsyncClient() as client:
            send_response = await client.post(external_api_url, json=batch_payload)
            send_response.raise_for_status()
            external_json = send_response.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi gửi dữ liệu ra API bên ngoài: {e}")

    return {
        "message": f"Đã xử lý hành động '{action}' thành công!",
        "sent_data": batch_payload,
        "external_response": external_json,
    }


@router.get("/{class_id}/exam/{exam_id}/user/{user_id}/results")
def get_user_result_history(
    class_id: int,
    exam_id: int,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Return the user's result history for the exam (all attempts), newest first.

    Access: admin, class teacher, or the user themself.
    Returns JSON: {"count": int, "results": [ {result fields..., "avg_speed": float|null}, ... ]}
    """
    # validate exam exists
    exam = exam_service.get_exam(db, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    # ensure class exists and exam is linked to this class
    db_class = db.get(Class, class_id)
    if not db_class:
        raise HTTPException(status_code=404, detail="Class not found")
    linked = db.exec(select(ClassExam).where((ClassExam.class_id == class_id) & (ClassExam.exam_id == exam_id))).first()
    if not linked:
        raise HTTPException(status_code=404, detail="Exam not linked to the provided class")

    # permission check relative to this class
    if current_user.user_role == UserRole.admin:
        pass
    elif current_user.user_role == UserRole.teacher:
        if db_class.teacher_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Not enough permissions")
    else:
        if current_user.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not enough permissions")

    # fetch results history ordered by newest first
    stmt = (
        select(Result)
        .where((Result.user_id == user_id) & (Result.exam_id == exam_id))
        .order_by(Result.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    rows = db.exec(stmt).all()

    if not rows:
        raise HTTPException(status_code=404, detail="No results found for this user and exam")

    out = []
    for res in rows:
        out.append({
            "result_id": getattr(res, "result_id", None),
            "user_id": getattr(res, "user_id", None),
            "exam_id": getattr(res, "exam_id", None),
            "step": getattr(res, "step", None),
            "lap": getattr(res, "lap", None),
            "start_time": getattr(res, "start_time", None),
            "end_time": getattr(res, "end_time", None),
            "avg_speed": compute_avg_speed(getattr(res, "start_time", None), getattr(res, "end_time", None), getattr(res, "lap", 1)),
            "created_at": getattr(res, "created_at", None),
            "updated_at": getattr(res, "updated_at", None),
        })

    return {"count": len(out), "results": out}


@router.get("/{class_id}/exam/{exam_id}/user/{user_id}/result_present")
def get_user_latest_result(
    class_id: int,
    exam_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Return the newest result of the user for an exam (class-scoped).
    """
    exam = exam_service.get_exam(db, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    # ensure class exists and the exam is linked to this class
    db_class = db.get(Class, class_id)
    if not db_class:
        raise HTTPException(status_code=404, detail="Class not found")
    linked = db.exec(select(ClassExam).where((ClassExam.class_id == class_id) & (ClassExam.exam_id == exam_id))).first()
    if not linked:
        raise HTTPException(status_code=404, detail="Exam not linked to the provided class")

    # permissions relative to this class
    if current_user.user_role == UserRole.teacher:
        if db_class.teacher_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Not enough permissions")
    elif current_user.user_role != UserRole.admin:
        if current_user.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not enough permissions")

    # chỉ lấy 1 result mới nhất
    stmt = (
        select(Result)
        .where((Result.user_id == user_id) & (Result.exam_id == exam_id))
        .order_by(Result.created_at.desc())
        .limit(1)
    )
    result = db.exec(stmt).first()

    if not result:
        raise HTTPException(status_code=404, detail="No results found for this user and exam")

    out = {
        "result_id": result.result_id,
        "user_id": result.user_id,
        "exam_id": result.exam_id,
        "step": result.step,
        "lap": result.lap,
        "start_time": result.start_time,
        "end_time": result.end_time,
        "avg_speed": compute_avg_speed(result.start_time, result.end_time, result.lap),
        "created_at": result.created_at,
        "updated_at": result.updated_at,
    }

    return out



