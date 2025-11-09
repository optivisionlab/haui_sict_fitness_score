from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel
from app.models.classes import CourseType, ClassStatus


class ClassCreate(BaseModel):
    class_name: str
    course_type: CourseType = CourseType.running
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    description: Optional[str] = None
    teacher_id: Optional[int] = None
    class_status: ClassStatus = ClassStatus.active


class ClassRead(BaseModel):
    class_id: int
    class_name: str
    course_type: CourseType
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    description: Optional[str] = None
    teacher_id: Optional[int] = None
    class_status: ClassStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ClassUpdate(BaseModel):
    class_name: Optional[str] = None
    course_type: Optional[CourseType] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    description: Optional[str] = None
    teacher_id: Optional[int] = None
    class_status: Optional[ClassStatus] = None