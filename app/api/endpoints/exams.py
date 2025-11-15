from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlmodel import Session, select
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User, UserRole
from app.models.exams import Exam, ClassExam
from app.models.classes import Class
from app.models.result import Result
from app.schemas.exams import (
	ExamCreate,
	ExamRead,
	ExamUpdate,
)
from app.schemas.results import (
	ResultCreate,
	ResultRead,
	ResultUpdate,
)
from app.services import exam_service, result_service
from datetime import datetime
import httpx
from app.services.result_service import compute_avg_speed
from pydantic import BaseModel, Field



router = APIRouter()


@router.get("/", response_model=List[ExamRead])
def list_exams(
	class_id: Optional[int] = Query(None, description="Optional class_id to filter exams"),
	skip: int = 0,
	limit: int = 100,
	db: Session = Depends(get_db),
) -> Any:
	exams = exam_service.list_exams(db, class_id=class_id, skip=skip, limit=limit)
	return exams


@router.post("/", response_model=ExamRead)
def create_exam(
	exam_in: ExamCreate,
	class_id: Optional[int] = Query(None, description="Optional class_id to link the exam to a class"),
	current_user: User = Depends(get_current_user),
	db: Session = Depends(get_db),
) -> Any:
	"""Create an exam. If `class_id` is provided the caller must be the
	class teacher or admin; creating an unlinked exam requires admin.
	"""
	# If creating linked exam, validate permissions against the class
	if class_id is not None:
		db_class = db.get(Class, class_id)
		if not db_class:
			raise HTTPException(status_code=404, detail="Class not found")
		if not (current_user.user_role == UserRole.admin or db_class.teacher_id == current_user.user_id):
			raise HTTPException(status_code=403, detail="Not enough permissions")
	else:
		# creating an unlinked exam: only admin allowed
		if current_user.user_role != UserRole.admin:
			raise HTTPException(status_code=403, detail="Not enough permissions")

	exam = exam_service.create_exam(db, exam_in, class_id=class_id)
	return exam


@router.get("/{exam_id}", response_model=ExamRead)
def get_exam(exam_id: int, db: Session = Depends(get_db)) -> Any:
	exam = exam_service.get_exam(db, exam_id)
	if not exam:
		raise HTTPException(status_code=404, detail="Exam not found")
	return exam


def _get_linked_classes(db: Session, exam_id: int) -> List[Class]:
	return db.exec(select(Class).join(ClassExam, Class.class_id == ClassExam.class_id).where(ClassExam.exam_id == exam_id)).all()


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
		# permission: admin or teacher of at least one linked class
		if current_user.user_role == UserRole.admin:
			pass
		elif current_user.user_role == UserRole.teacher:
			allowed = any(c.teacher_id == current_user.user_id for c in linked_classes)
			if not allowed:
				raise HTTPException(status_code=403, detail="Not enough permissions")
		else:
			raise HTTPException(status_code=403, detail="Not enough permissions")
	else:
		# no linked classes: only admin may update
		if current_user.user_role != UserRole.admin:
			raise HTTPException(status_code=403, detail="Not enough permissions")

	exam = exam_service.update_exam(db, exam_id, exam_in)
	return exam


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
		if current_user.user_role == UserRole.admin:
			pass
		elif current_user.user_role == UserRole.teacher:
			allowed = any(c.teacher_id == current_user.user_id for c in linked_classes)
			if not allowed:
				raise HTTPException(status_code=403, detail="Not enough permissions")
		else:
			raise HTTPException(status_code=403, detail="Not enough permissions")
	else:
		if current_user.user_role != UserRole.admin:
			raise HTTPException(status_code=403, detail="Not enough permissions")

	exam_service.delete_exam(db, exam_id)
	return {"message": "Exam deleted successfully"}


### Results endpoints for exam


@router.get("/{exam_id}/results", response_model=List[ResultRead])
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

	if current_user.user_role == UserRole.admin:
		pass
	elif current_user.user_role == UserRole.teacher:
		allowed = any(c.teacher_id == current_user.user_id for c in linked_classes)
		if not allowed:
			raise HTTPException(status_code=403, detail="Not enough permissions")
	else:
		raise HTTPException(status_code=403, detail="Not enough permissions")

	results = result_service.list_results(db, exam_id=exam_id, skip=skip, limit=limit)
	return results


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
		allowed = any(c.teacher_id == current_user.user_id for c in linked_classes)
		if not allowed:
			raise HTTPException(status_code=403, detail="Not enough permissions")
	else:
		if current_user.user_id != result_in.user_id:
			raise HTTPException(status_code=403, detail="Not enough permissions")

	if result_in.exam_id != exam_id:
		raise HTTPException(status_code=400, detail="exam_id in body must match path")

	created = result_service.create_result(db, result_in)
	return created


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
		allowed = any(c.teacher_id == current_user.user_id for c in linked_classes)
		if not allowed:
			raise HTTPException(status_code=403, detail="Not enough permissions")
	else:
		if current_user.user_id != result.user_id:
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

	if current_user.user_role == UserRole.admin:
		pass
	elif current_user.user_role == UserRole.teacher:
		allowed = any(c.teacher_id == current_user.user_id for c in linked_classes)
		if not allowed:
			raise HTTPException(status_code=403, detail="Not enough permissions")
	else:
		raise HTTPException(status_code=403, detail="Not enough permissions")

	updated = result_service.update_result(db, result_id, result_in)
	return updated


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

	if current_user.user_role == UserRole.admin:
		pass
	elif current_user.user_role == UserRole.teacher:
		allowed = any(c.teacher_id == current_user.user_id for c in linked_classes)
		if not allowed:
			raise HTTPException(status_code=403, detail="Not enough permissions")
	else:
		raise HTTPException(status_code=403, detail="Not enough permissions")

	result_service.delete_result(db, result_id)
	return {"message": "Result deleted successfully"}



class BatchUserPayload(BaseModel):
	# The external API expects string IDs in the example payload; accept them as strings
	user_id: str = Field(..., description="User identifier as string")
	exam_id: str = Field(..., description="Exam identifier as string")
	step: int = Field(..., ge=1, description="Step number (positive integer)")
	start_time: Optional[str] = Field(None, description="ISO datetime string for start action")
	end_time: Optional[str] = Field(None, description="ISO datetime string for end action")


@router.post("/{exam_id}/user/{user_id}/{step}/{action}")
async def handle_exam_action(
	exam_id: int,
	user_id: int,
	step: int,
	action: str,
	payload: BatchUserPayload = Body(..., description="Payload containing user_id, exam_id and either start_time or end_time depending on action"),
):
	"""
	action: 'start' hoặc 'end'
	This endpoint forwards the provided payload to an external service. It no longer
	calls any local API — the caller must include the necessary fields in the request body.
	"""
	if action not in ["start", "end"]:
		raise HTTPException(status_code=400, detail="Hành động không hợp lệ (chỉ cho phép: start hoặc end)")

	# NOTE: request body is authoritative per new contract. We'll use payload values directly.
	# Validate that path params are present (they are required by route) but do not override body.
	# Pydantic already validated step >= 1 and required fields; still check action value.

	# Ensure required action-specific time exists and build user_record
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

@router.get("/{exam_id}/user/{user_id}/results")
def get_user_result_history(
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

	# ensure exam is linked to at least one class
	linked_classes = _get_linked_classes(db, exam_id)
	if not linked_classes:
		raise HTTPException(status_code=404, detail="Class not found for this exam")

	# permission check
	if current_user.user_role == UserRole.admin:
		pass
	elif current_user.user_role == UserRole.teacher:
		allowed = any(c.teacher_id == current_user.user_id for c in linked_classes)
		if not allowed:
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


@router.get("/{exam_id}/user/{user_id}/result_present")
def get_user_latest_result(
    exam_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Return the newest result of the user for an exam."""

    exam = exam_service.get_exam(db, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    linked_classes = _get_linked_classes(db, exam_id)
    if not linked_classes:
        raise HTTPException(status_code=404, detail="Class not found for this exam")

    # permissions
    if current_user.user_role == UserRole.teacher:
        allowed = any(c.teacher_id == current_user.user_id for c in linked_classes)
        if not allowed:
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



