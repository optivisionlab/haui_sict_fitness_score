"""Class business logic: CRUD, enrollment, result queries."""

import logging
from typing import Optional

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import and_
from sqlmodel import Session, select

from app.core.exceptions import (
    AlreadyExistsException,
    InvalidInputException,
    NotFoundException,
)
from app.models.camera import CameraUserClass
from app.models.classes import Class
from app.models.exams import ClassExam, Exam
from app.models.result import Result
from app.models.user import User, UserClass, UserRole, UserStatus
from app.schemas.classes import ClassCreate, ClassUpdate
from app.services.result_service import compute_avg_speed
from app.utils.formatters import (
    format_result_history_item,
    format_result_item,
    format_result_simple,
    format_result_with_user,
    format_user_info,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Basic CRUD
# ---------------------------------------------------------------------------


def get_class(db: Session, class_id: int) -> Optional[Class]:
    return db.get(Class, class_id)


def list_classes(
    db: Session,
    current_user: User,
    *,
    skip: int = 0,
    limit: int = 100,
    teacher_id: Optional[int] = None,
    student_id: Optional[int] = None,
    course_type: Optional[str] = None,
) -> list[Class]:
    """List classes with role-based filtering."""
    if current_user.user_role == UserRole.admin:
        q = select(Class)
        if student_id is not None:
            q = q.join(UserClass, Class.class_id == UserClass.class_id).where(UserClass.user_id == student_id)
            if course_type:
                q = q.where(UserClass.course_type == course_type)
        if teacher_id is not None:
            q = q.where(Class.teacher_id == teacher_id)
        return db.exec(q.offset(skip).limit(limit)).all()

    if current_user.user_role == UserRole.teacher:
        q = select(Class).where(Class.teacher_id == current_user.user_id)
        return db.exec(q.offset(skip).limit(limit)).all()

    # Student: enrolled classes
    q = (
        select(Class)
        .join(UserClass, Class.class_id == UserClass.class_id)
        .where(UserClass.user_id == current_user.user_id)
    )
    if course_type:
        q = q.where(UserClass.course_type == course_type)
    return db.exec(q.offset(skip).limit(limit)).all()


def create_class(db: Session, class_in: ClassCreate) -> Class:
    """Create a new class. Validates teacher_id if provided."""
    teacher_id = class_in.teacher_id
    if teacher_id is not None:
        teacher = db.get(User, teacher_id)
        if not teacher:
            raise InvalidInputException("teacher_id does not exist")
        if teacher.user_role not in (UserRole.teacher, UserRole.admin):
            raise InvalidInputException("Assigned teacher must have role 'teacher' or 'admin'")

    db_class = Class(**class_in.model_dump())
    db.add(db_class)
    db.commit()
    db.refresh(db_class)
    return db_class


def update_class(db: Session, class_id: int, class_in: ClassUpdate) -> Class:
    db_class = get_class(db, class_id)
    if not db_class:
        raise NotFoundException("Class")

    update_data = class_in.model_dump(exclude_unset=True)
    if "teacher_id" in update_data and update_data["teacher_id"] is not None:
        teacher = db.get(User, update_data["teacher_id"])
        if not teacher:
            raise InvalidInputException("teacher_id does not exist")
        if teacher.user_role not in (UserRole.teacher, UserRole.admin):
            raise InvalidInputException("Assigned teacher must have role 'teacher' or 'admin'")

    for field, value in update_data.items():
        setattr(db_class, field, value)

    db.add(db_class)
    db.commit()
    db.refresh(db_class)
    return db_class


def delete_class(db: Session, class_id: int) -> None:
    """Delete class with cascading cleanup of related data."""
    db_class = get_class(db, class_id)
    if not db_class:
        raise NotFoundException("Class")

    try:
        db.exec(text("DELETE FROM user_class WHERE class_id = :cid"), {"cid": class_id})

        rows = db.exec(text("SELECT exam_id FROM class_exam WHERE class_id = :cid"), {"cid": class_id}).all()
        exam_ids = [r[0] if isinstance(r, tuple) else getattr(r, "exam_id", None) for r in rows]

        if exam_ids:
            params = {f"id{i}": eid for i, eid in enumerate(exam_ids)}
            in_clause = ",".join(f":id{i}" for i in range(len(exam_ids)))
            db.exec(text(f"DELETE FROM results WHERE exam_id IN ({in_clause})"), params)

        db.exec(text("DELETE FROM class_exam WHERE class_id = :cid"), {"cid": class_id})

        if exam_ids:
            params = {f"id{i}": eid for i, eid in enumerate(exam_ids)}
            in_clause = ",".join(f":id{i}" for i in range(len(exam_ids)))
            db.exec(
                text(
                    f"DELETE FROM exams WHERE exam_id IN ({in_clause}) "
                    f"AND NOT EXISTS (SELECT 1 FROM class_exam ce WHERE ce.exam_id = exams.exam_id)"
                ),
                params,
            )

        db.delete(db_class)
        db.commit()
    except Exception:
        db.rollback()
        raise


# ---------------------------------------------------------------------------
# Enrollment
# ---------------------------------------------------------------------------


def enroll_student(db: Session, class_id: int, user_id: int) -> None:
    """Enroll a student in a class with validation."""
    db_class = get_class(db, class_id)
    if not db_class:
        raise NotFoundException("Class")

    student = db.get(User, user_id)
    if not student:
        raise NotFoundException("Student")

    if student.user_role != UserRole.student:
        raise InvalidInputException("User is not a student and cannot be enrolled")

    if student.user_status != UserStatus.active:
        raise InvalidInputException("Student is not active and cannot be enrolled")

    if db_class.class_status != "active":
        raise InvalidInputException("Cannot enroll into a non-active class")

    existing = db.exec(
        select(UserClass).where((UserClass.class_id == class_id) & (UserClass.user_id == user_id))
    ).first()
    if existing:
        raise AlreadyExistsException("Student already enrolled in this class")

    user_class = UserClass(class_id=class_id, user_id=user_id)
    db.add(user_class)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AlreadyExistsException("Student already enrolled (concurrent request)")


def add_exam_to_class(db: Session, class_id: int, exam_id: int) -> None:
    """Link an existing exam to a class."""
    db_class = get_class(db, class_id)
    if not db_class:
        raise NotFoundException("Class")

    exam = db.get(Exam, exam_id)
    if not exam:
        raise NotFoundException("Exam")

    if db_class.class_status != "active":
        raise InvalidInputException("Cannot add exam to a non-active class")

    existing = db.exec(
        select(ClassExam).where((ClassExam.class_id == class_id) & (ClassExam.exam_id == exam_id))
    ).first()
    if existing:
        raise AlreadyExistsException("Exam already added to this class")

    class_exam = ClassExam(class_id=class_id, exam_id=exam_id)
    db.add(class_exam)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AlreadyExistsException("Exam already added (concurrent request)")


# ---------------------------------------------------------------------------
# Result queries (moved from classes endpoint)
# ---------------------------------------------------------------------------


def get_user_results_in_class(
    db: Session, class_id: int, user_id: int, *, skip: int = 0, limit: int = 100
) -> dict:
    """Return a user's results for exams in the given class + user info."""
    user = db.get(User, user_id)
    if not user:
        raise NotFoundException("User")

    q = (
        select(Exam, Result, ClassExam)
        .join(ClassExam, Exam.exam_id == ClassExam.exam_id)
        .outerjoin(Result, and_(Result.exam_id == Exam.exam_id, Result.user_id == user_id))
        .where(ClassExam.class_id == class_id)
        .order_by(Result.created_at.desc().nullslast())
        .offset(skip)
        .limit(limit)
    )
    rows = db.exec(q).all()

    results = [format_result_item(res, exam, ce) for exam, res, ce in rows]
    return {"user": format_user_info(user), "results": results}


def get_user_top_results_per_exam(
    db: Session, class_id: int, user_id: int, *, skip: int = 0, limit: int = 100
) -> dict:
    """Return the user's best result per exam in a class (by avg_speed)."""
    user = db.get(User, user_id)
    if not user:
        raise NotFoundException("User")

    q = (
        select(Exam, Result, ClassExam, Class, UserClass)
        .join(ClassExam, Exam.exam_id == ClassExam.exam_id)
        .join(Class, ClassExam.class_id == Class.class_id)
        .join(UserClass, Class.class_id == UserClass.class_id)
        .outerjoin(Result, and_(Result.exam_id == Exam.exam_id, Result.user_id == user_id))
        .where(ClassExam.class_id == class_id, UserClass.user_id == user_id, UserClass.course_type == "running")
        .order_by(Result.created_at.desc().nullslast())
        .offset(skip)
        .limit(limit)
    )
    rows = db.exec(q).all()

    best_by_exam: dict = {}
    for exam, res, ce, cls, uc in rows:
        eid = exam.exam_id
        speed = compute_avg_speed(res.start_time, res.end_time, res.lap or 1) if res else None
        speed_val = speed if speed is not None else -1.0

        cur = best_by_exam.get(eid)
        if cur is None or speed_val > cur["speed"]:
            best_by_exam[eid] = {"exam": exam, "class_exam": ce, "result": res, "speed": speed_val}
        elif speed_val == cur["speed"] and res:
            prev = cur["result"]
            if not getattr(prev, "created_at", None) or (
                getattr(res, "created_at", None) and res.created_at > prev.created_at
            ):
                best_by_exam[eid] = {"exam": exam, "class_exam": ce, "result": res, "speed": speed_val}

    results = [
        format_result_item(info["result"], info["exam"], info["class_exam"])
        for info in best_by_exam.values()
    ]
    return {"user": format_user_info(user), "results": results}


def get_user_exam_results(db: Session, class_id: int, user_id: int, exam_id: int) -> dict:
    """Return detailed result rows for user/exam/class."""
    q = (
        select(Result, Exam, Class, User)
        .join(Exam, Result.exam_id == Exam.exam_id)
        .join(ClassExam, Exam.exam_id == ClassExam.exam_id)
        .join(Class, ClassExam.class_id == Class.class_id)
        .join(User, Result.user_id == User.user_id)
        .where(Result.user_id == user_id, Class.class_id == class_id, Exam.exam_id == exam_id)
    )
    rows = db.exec(q).all()
    return {"rows": [format_result_with_user(res, us, ex, cl) for res, ex, cl, us in rows]}


def get_class_exam_results(
    db: Session, class_id: int, exam_id: int, *, skip: int = 0, limit: int = 100
) -> dict:
    """Return all results for a specific exam within a class."""
    q = (
        select(Result, User)
        .join(ClassExam, Result.exam_id == ClassExam.exam_id)
        .join(User, Result.user_id == User.user_id)
        .where(ClassExam.class_id == class_id, Result.exam_id == exam_id)
        .order_by(Result.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    rows = db.exec(q).all()

    out = []
    for res, us in rows:
        item = format_result_simple(res)
        item["user_id"] = res.user_id
        item["full_name"] = us.full_name
        out.append(item)

    return {"rows": out, "count": len(out)}


def get_class_exam_results_by_user(
    db: Session, class_id: int, exam_id: int, *, skip: int = 0, limit: int = 100
) -> dict:
    """Return exam results grouped per enrolled user."""
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

    grouped: dict = {}
    for user_obj, res in rows:
        uid = user_obj.user_id
        if uid not in grouped:
            grouped[uid] = {"user": format_user_info(user_obj), "results": []}
        if res is not None:
            grouped[uid]["results"].append(format_result_simple(res))

    out = list(grouped.values())
    return {"count": len(out), "items": out}


def get_class_exam_top_by_user(
    db: Session, class_id: int, exam_id: int, *, skip: int = 0, limit: int = 100
) -> dict:
    """Return best result per enrolled user for an exam (by avg_speed)."""
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

    grouped: dict = {}
    for user_obj, res in rows:
        uid = user_obj.user_id
        if uid not in grouped:
            grouped[uid] = {"user": format_user_info(user_obj), "_top_result": None, "_top_speed": None}

        if res is None:
            continue

        speed = compute_avg_speed(res.start_time, res.end_time, res.lap or 1)
        speed_val = speed if speed is not None else -1.0

        if grouped[uid]["_top_speed"] is None or speed_val > grouped[uid]["_top_speed"]:
            grouped[uid]["_top_result"] = res
            grouped[uid]["_top_speed"] = speed_val
        elif speed_val == grouped[uid]["_top_speed"]:
            prev = grouped[uid]["_top_result"]
            if not getattr(prev, "created_at", None) or (
                getattr(res, "created_at", None) and res.created_at > prev.created_at
            ):
                grouped[uid]["_top_result"] = res

    out = []
    for uid, info in grouped.items():
        top = info["_top_result"]
        result_data = format_result_simple(top) if top else None
        out.append({"user": info["user"], "result": result_data})

    return {"count": len(out), "items": out}


def get_selected_exams_results_by_user(
    db: Session, class_id: int, *, requested_exam_ids: list[int], skip: int = 0, limit: int = 100
) -> dict:
    """Return results for specific exams for all users in the class."""
    rows = db.exec(
        select(ClassExam.exam_id).where(
            (ClassExam.class_id == class_id) & (ClassExam.exam_id.in_(requested_exam_ids))
        )
    ).all()
    linked_ids = [r[0] if isinstance(r, tuple) else r for r in rows]
    if not linked_ids:
        raise NotFoundException(detail="Requested exams are not linked to this class")

    stmt = (
        select(User, Result, Exam, ClassExam)
        .join(UserClass, User.user_id == UserClass.user_id)
        .outerjoin(Result, (Result.user_id == User.user_id) & (Result.exam_id.in_(linked_ids)))
        .outerjoin(Exam, Result.exam_id == Exam.exam_id)
        .outerjoin(ClassExam, (ClassExam.exam_id == Exam.exam_id) & (ClassExam.class_id == class_id))
        .where(UserClass.class_id == class_id)
        .order_by(User.full_name)
        .offset(skip)
        .limit(limit)
    )
    rows = db.exec(stmt).all()

    grouped: dict = {}
    for user_obj, res, ex, ce in rows:
        uid = user_obj.user_id
        if uid not in grouped:
            grouped[uid] = {"user": format_user_info(user_obj), "results": []}
        if res is not None:
            grouped[uid]["results"].append(format_result_item(res, ex, ce))

    out = list(grouped.values())
    return {"count": len(out), "items": out}


def get_user_result_history(
    db: Session, user_id: int, exam_id: int, *, skip: int = 0, limit: int = 100
) -> dict:
    """Return user's result history for an exam (newest first)."""
    stmt = (
        select(Result)
        .where((Result.user_id == user_id) & (Result.exam_id == exam_id))
        .order_by(Result.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    rows = db.exec(stmt).all()

    if not rows:
        raise NotFoundException(detail="No results found for this user and exam")

    return {"count": len(rows), "results": [format_result_history_item(r) for r in rows]}


def get_user_latest_result(db: Session, user_id: int, exam_id: int) -> dict:
    """Return the newest result for user/exam."""
    stmt = (
        select(Result)
        .where((Result.user_id == user_id) & (Result.exam_id == exam_id))
        .order_by(Result.created_at.desc())
        .limit(1)
    )
    result = db.exec(stmt).first()
    if not result:
        raise NotFoundException(detail="No results found for this user and exam")

    return format_result_history_item(result)


def get_user_checkin_images(db: Session, class_id: int, exam_id: int, user_id: int) -> dict:
    """Return check-in images for a user within a class and exam."""
    stmt = (
        select(CameraUserClass)
        .where(
            (CameraUserClass.user_id == user_id)
            & (CameraUserClass.class_id == class_id)
            & (CameraUserClass.exam_id == exam_id)
        )
        .order_by(CameraUserClass.checkin_time.desc())
    )
    rows = db.exec(stmt).all()

    images = [
        {
            "camera_id": r.camera_id,
            "checkin_time": r.checkin_time.isoformat() if r.checkin_time else None,
            "image_url": r.image_url,
        }
        for r in rows
    ]
    return {"count": len(images), "images": images}


def get_exams_for_class(db: Session, class_id: int) -> dict:
    """Return all exams linked to a class including exam_date."""
    q = (
        select(Exam, ClassExam)
        .join(ClassExam, Exam.exam_id == ClassExam.exam_id)
        .where(ClassExam.class_id == class_id)
        .order_by(ClassExam.exam_date)
    )
    rows = db.exec(q).all()

    items = [
        {
            "exam_id": exam.exam_id,
            "title": exam.title,
            "description": exam.description,
            "exam_date": ce.exam_date,
        }
        for exam, ce in rows
    ]
    return {"count": len(items), "items": items}
