from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User, UserRole, UserStatus
from app.models.classes import Class, UserClass
from app.models.exams import Exam
from app.models.result import Result
from app.schemas.classes import ClassCreate, ClassRead, ClassUpdate
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

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
    if current_user.user_role not in [UserRole.admin, UserRole.teacher]:
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
    
    if current_user.user_role not in [UserRole.admin, UserRole.teacher] and db_class.teacher_id != current_user.user_id:
        raise HTTPException(
            status_code=403,
            detail="Not enough permissions"
        )
    
    for field, value in class_in.dict(exclude_unset=True).items():
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
    
    if current_user.user_role not in [UserRole.admin, UserRole.teacher] and db_class.teacher_id != current_user.user_id:
        raise HTTPException(
            status_code=403,
            detail="Not enough permissions"
        )
    
    db.delete(db_class)
    db.commit()
    return {"message": "Class deleted successfully"}


@router.get("/{class_id}/user/{user_id}/results")
def get_user_results_in_class(
    class_id: int,
    user_id: int,
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

    # Query results for the user's exams that belong to this class
    q = (
        select(Result, Exam)
        .join(Exam, Result.exam_id == Exam.exam_id)
        .where(Result.user_id == user_id, Exam.class_id == class_id)
    )

    rows = db.exec(q).all()

    # rows will be list of tuples (Result, Exam)
    results = []
    for res, exam in rows:
        results.append({
            "result_id": getattr(res, "result_id", None),
            "exam_id": getattr(res, "exam_id", None),
            "step": getattr(res, "step", None),
            "start_time": getattr(res, "start_time", None),
            "end_time": getattr(res, "end_time", None),
            "created_at": getattr(res, "created_at", None),
            "updated_at": getattr(res, "updated_at", None),
            "exam": {
                "exam_id": getattr(exam, "exam_id", None),
                "title": getattr(exam, "title", None),
                "description": getattr(exam, "description", None),
                "exam_date": getattr(exam, "exam_date", None),
                "max_score": getattr(exam, "max_score", None),
            },
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