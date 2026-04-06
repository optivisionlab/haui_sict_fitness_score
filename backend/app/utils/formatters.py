"""Helper functions for formatting model objects into response dicts.

Eliminates repetitive getattr(..., None) + compute_avg_speed patterns
that were duplicated across many endpoints.
"""

from typing import Optional

from app.models.exams import Exam, ClassExam
from app.models.result import Result
from app.models.user import User
from app.services.result_service import compute_avg_speed


def format_user_info(user: User) -> dict:
    """Format a User model into a compact info dict."""
    return {
        "user_id": user.user_id,
        "user_name": user.user_name,
        "full_name": user.full_name,
        "email": user.email,
        "phone_number": user.phone_number,
        "user_code": user.user_code,
    }


def format_result_item(
    result: Optional[Result],
    exam: Optional[Exam] = None,
    class_exam: Optional[ClassExam] = None,
) -> dict:
    """Format a Result into a response dict with computed avg_speed.

    If result is None, returns a dict with null values (exam info preserved).
    """
    if result:
        return {
            "result_id": result.result_id,
            "exam_id": result.exam_id,
            "exam_title": exam.title if exam else None,
            "exam_description": exam.description if exam else None,
            "exam_date": class_exam.exam_date if class_exam else None,
            "step": result.step,
            "lap": result.lap,
            "start_time": result.start_time,
            "end_time": result.end_time,
            "avg_speed": compute_avg_speed(result.start_time, result.end_time, result.lap or 1),
            "created_at": result.created_at,
        }

    return {
        "result_id": None,
        "exam_id": exam.exam_id if exam else None,
        "exam_title": exam.title if exam else None,
        "exam_description": exam.description if exam else None,
        "exam_date": class_exam.exam_date if class_exam else None,
        "step": None,
        "lap": None,
        "start_time": None,
        "end_time": None,
        "avg_speed": None,
        "created_at": None,
    }


def format_result_with_user(
    result: Result,
    user: User,
    exam: Optional[Exam] = None,
    class_obj=None,
) -> dict:
    """Format a result row that includes user and class info."""
    return {
        "result_id": result.result_id,
        "user_id": result.user_id,
        "full_name": user.full_name,
        "exam_id": result.exam_id,
        "exam_title": exam.title if exam else None,
        "class_id": class_obj.class_id if class_obj else None,
        "class_name": class_obj.class_name if class_obj else None,
        "step": result.step,
        "lap": result.lap,
        "start_time": result.start_time,
        "end_time": result.end_time,
        "avg_speed": compute_avg_speed(result.start_time, result.end_time, result.lap or 1),
        "created_at": result.created_at,
    }


def format_result_history_item(result: Result) -> dict:
    """Format a result for history listing (includes updated_at)."""
    return {
        "result_id": result.result_id,
        "user_id": result.user_id,
        "exam_id": result.exam_id,
        "step": result.step,
        "lap": result.lap,
        "start_time": result.start_time,
        "end_time": result.end_time,
        "avg_speed": compute_avg_speed(result.start_time, result.end_time, result.lap or 1),
        "created_at": result.created_at,
        "updated_at": result.updated_at,
    }


def format_result_simple(result: Result) -> dict:
    """Format a result with basic fields + avg_speed (no exam/user info)."""
    return {
        "result_id": result.result_id,
        "exam_id": result.exam_id,
        "step": result.step,
        "lap": result.lap,
        "start_time": result.start_time,
        "end_time": result.end_time,
        "avg_speed": compute_avg_speed(result.start_time, result.end_time, result.lap or 1),
        "created_at": result.created_at,
    }
