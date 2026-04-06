"""Shared response schemas used across multiple endpoints."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class UserInfoResponse(BaseModel):
    """Compact user info included in nested responses."""
    user_id: int
    user_name: str
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    user_code: Optional[str] = None

    class Config:
        from_attributes = True


class ResultItemResponse(BaseModel):
    """A single result item with computed avg_speed."""
    result_id: Optional[int] = None
    exam_id: Optional[int] = None
    exam_title: Optional[str] = None
    exam_description: Optional[str] = None
    exam_date: Optional[datetime] = None
    step: Optional[int] = None
    lap: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    avg_speed: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ResultWithUserResponse(BaseModel):
    """A result row that includes user info fields."""
    result_id: Optional[int] = None
    user_id: Optional[int] = None
    full_name: Optional[str] = None
    exam_id: Optional[int] = None
    exam_title: Optional[str] = None
    class_id: Optional[int] = None
    class_name: Optional[str] = None
    step: Optional[int] = None
    lap: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    avg_speed: Optional[float] = None
    created_at: Optional[datetime] = None


class UserResultsResponse(BaseModel):
    """User info + list of results."""
    user: UserInfoResponse
    results: list[ResultItemResponse]


class PaginatedResponse(BaseModel):
    """Generic paginated list response."""
    count: int
    items: list


class ExamInfoResponse(BaseModel):
    """Exam info as returned in class exam listing."""
    exam_id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    exam_date: Optional[datetime] = None
