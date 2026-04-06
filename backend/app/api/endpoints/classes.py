"""Class endpoints: CRUD, enrollment, exam linking, result queries.

Business logic is delegated to class_service. Permission checks use
core.dependencies.ClassPermissionChecker for consistency.
"""

import logging
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import (
    ClassPermissionChecker,
    require_admin,
    require_admin_or_teacher,
)
from app.core.security import get_current_user
from app.models.user import User, UserRole
from app.schemas.classes import ClassCreate, ClassRead, ClassUpdate
from app.services import class_service, exam_service

router = APIRouter()
logger = logging.getLogger(__name__)
_perm = ClassPermissionChecker


# ---------------------------------------------------------------------------
# Basic CRUD
# ---------------------------------------------------------------------------


@router.post("/", response_model=ClassRead)
def create_class(
    class_in: ClassCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Any:
    """Create a new class. Requires admin."""
    return class_service.create_class(db, class_in)


@router.get("/", response_model=list[ClassRead])
def list_classes(
    skip: int = 0,
    limit: int = 100,
    teacher_id: Optional[int] = None,
    student_id: Optional[int] = None,
    course_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """List classes (role-filtered)."""
    return class_service.list_classes(
        db,
        current_user,
        skip=skip,
        limit=limit,
        teacher_id=teacher_id,
        student_id=student_id,
        course_type=course_type,
    )


@router.get("/{class_id}", response_model=ClassRead)
def read_class(
    class_id: int,
    current_user: User = Depends(require_admin_or_teacher),
    db: Session = Depends(get_db),
) -> Any:
    """Get class by ID. Requires admin or teacher."""
    from app.core.exceptions import NotFoundException

    db_class = class_service.get_class(db, class_id)
    if not db_class:
        raise NotFoundException("Class")
    return db_class


@router.put("/{class_id}", response_model=ClassRead)
def update_class(
    class_id: int,
    class_in: ClassUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Any:
    """Update a class. Requires admin."""
    return class_service.update_class(db, class_id, class_in)


@router.delete("/{class_id}")
def delete_class(
    class_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Any:
    """Delete a class with cascading cleanup. Requires admin."""
    class_service.delete_class(db, class_id)
    return {"message": "Class deleted successfully"}


# ---------------------------------------------------------------------------
# Enrollment & Exam linking
# ---------------------------------------------------------------------------


@router.post("/{class_id}/enroll/{user_id}")
def enroll_student(
    class_id: int,
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Any:
    """Enroll a student in a class. Requires admin."""
    class_service.enroll_student(db, class_id, user_id)
    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"message": "Student enrolled successfully"})


@router.post("/{class_id}/add/{exam_id}")
def add_exam_to_class(
    class_id: int,
    exam_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Add an existing exam to a class. Requires admin or class teacher."""
    db_class = _perm.verify_class_access(db, class_id, current_user, require_teacher=True)
    class_service.add_exam_to_class(db, class_id, exam_id)
    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"message": "Exam added successfully"})


@router.get("/{class_id}/exams")
def get_exams_for_class(
    class_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Return all exams linked to a class. Accessible by admin, teacher, or enrolled student."""
    _perm.verify_class_access(db, class_id, current_user, allow_enrolled_student=True)
    return class_service.get_exams_for_class(db, class_id)


# ---------------------------------------------------------------------------
# Result queries
# ---------------------------------------------------------------------------


@router.get("/{class_id}/user/{user_id}/results")
def get_user_results_in_class(
    class_id: int,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Return a user's results for exams in the class."""
    _perm.verify_class_access(db, class_id, current_user, allow_enrolled_student=True)
    return class_service.get_user_results_in_class(db, class_id, user_id, skip=skip, limit=limit)


@router.get("/{class_id}/user/{user_id}/exams/results/top")
def get_user_top_results(
    class_id: int,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Return user's best results per exam in a class."""
    db_class = _perm.verify_class_access(db, class_id, current_user)
    if current_user.user_role == UserRole.student and current_user.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return class_service.get_user_top_results_per_exam(db, class_id, user_id, skip=skip, limit=limit)


@router.get("/{class_id}/user/{user_id}/exam/{exam_id}/results")
def get_user_exam_results(
    class_id: int,
    user_id: int,
    exam_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Return result rows for a specific user/exam/class."""
    db_class = _perm.verify_class_access(db, class_id, current_user)
    if current_user.user_role == UserRole.student and current_user.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return class_service.get_user_exam_results(db, class_id, user_id, exam_id)


@router.get("/{class_id}/exam/{exam_id}/results")
def get_class_exam_results(
    class_id: int,
    exam_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Return all results for an exam in the class. Requires admin or class teacher."""
    _perm.verify_class_access(db, class_id, current_user, require_teacher=True)
    return class_service.get_class_exam_results(db, class_id, exam_id, skip=skip, limit=limit)


@router.get("/{class_id}/exam/{exam_id}/results/by-user")
def get_class_exam_results_by_user(
    class_id: int,
    exam_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Return exam results grouped by user."""
    _perm.verify_class_access(db, class_id, current_user, allow_enrolled_student=True)
    _perm.verify_exam_linked_to_class(db, class_id, exam_id)
    return class_service.get_class_exam_results_by_user(db, class_id, exam_id, skip=skip, limit=limit)


@router.get("/{class_id}/exam/{exam_id}/results/by-user/top")
def get_class_exam_top_by_user(
    class_id: int,
    exam_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Return top result per user for an exam. Requires admin or class teacher."""
    _perm.verify_class_access(db, class_id, current_user, require_teacher=True)
    _perm.verify_exam_linked_to_class(db, class_id, exam_id)
    return class_service.get_class_exam_top_by_user(db, class_id, exam_id, skip=skip, limit=limit)


@router.get("/{class_id}/exams/results/by-user")
def get_selected_exams_results_by_user(
    class_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Return results for exams [1,2,3] for all users in the class."""
    _perm.verify_class_access(db, class_id, current_user, allow_enrolled_student=True)
    return class_service.get_selected_exams_results_by_user(
        db, class_id, requested_exam_ids=[1, 2, 3], skip=skip, limit=limit
    )


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
    """Return user's result history for an exam (newest first)."""
    db_class = _perm.verify_class_access(db, class_id, current_user, require_teacher=True)
    _perm.verify_exam_linked_to_class(db, class_id, exam_id)
    # Allow student to view own results
    if current_user.user_role == UserRole.student and current_user.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return class_service.get_user_result_history(db, user_id, exam_id, skip=skip, limit=limit)


@router.get("/{class_id}/exam/{exam_id}/user/{user_id}/result_present")
def get_user_latest_result(
    class_id: int,
    exam_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Return the newest result of the user for an exam."""
    db_class = _perm.verify_class_access(db, class_id, current_user)
    _perm.verify_exam_linked_to_class(db, class_id, exam_id)
    if current_user.user_role == UserRole.student and current_user.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return class_service.get_user_latest_result(db, user_id, exam_id)


@router.get("/{class_id}/exam/{exam_id}/user/{user_id}/checkin-images")
def get_user_checkin_images(
    class_id: int,
    exam_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Return check-in images for a user within a class and exam."""
    db_class = _perm.verify_class_access(db, class_id, current_user)
    _perm.verify_exam_linked_to_class(db, class_id, exam_id)
    if current_user.user_role == UserRole.student and current_user.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return class_service.get_user_checkin_images(db, class_id, exam_id, user_id)


# ---------------------------------------------------------------------------
# External API integration
# ---------------------------------------------------------------------------


class BatchUserPayload(BaseModel):
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
    payload: BatchUserPayload = Body(...),
    db: Session = Depends(get_db),
) -> Any:
    """Forward exam start/end action to external tracking API."""
    if action not in ("start", "end"):
        raise HTTPException(status_code=400, detail="Invalid action (allowed: start, end)")

    if action == "start" and not payload.start_time:
        raise HTTPException(status_code=400, detail="Missing start_time in payload")
    if action == "end" and not payload.end_time:
        raise HTTPException(status_code=400, detail="Missing end_time in payload")

    _perm.verify_class_access(db, class_id, User(user_role="admin", user_id=0))  # minimal check
    _perm.verify_exam_linked_to_class(db, class_id, exam_id)

    user_record: dict = {
        "user_id": str(payload.user_id),
        "exam_id": str(payload.exam_id),
        "class_id": class_id,
        "step": int(payload.step),
    }
    if payload.start_time:
        user_record["start_time"] = payload.start_time
    if payload.end_time:
        user_record["end_time"] = payload.end_time

    batch_payload = {"users": [user_record]}

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(settings.EXTERNAL_TRACKING_API_URL, json=batch_payload)
            resp.raise_for_status()
            external_json = resp.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"External API error: {e}")

    return {
        "message": f"Action '{action}' processed successfully",
        "sent_data": batch_payload,
        "external_response": external_json,
    }
