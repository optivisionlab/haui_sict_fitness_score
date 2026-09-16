"""Pydantic v2 contracts for the public API."""
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str | None = None
    email: str | None = None
    password: str


class UserInput(BaseModel):
    username: str
    password: str
    name: str
    email: str | None = None
    role: Literal["student", "teacher", "admin"] = "student"
    studentCode: str | None = None


class SportInput(BaseModel):
    code: str
    name: str
    scoringConfig: dict[str, Any] = Field(default_factory=dict)


class SportPatch(BaseModel):
    name: str | None = None
    scoringConfig: dict[str, Any] | None = None


class CourseInput(BaseModel):
    key: str | None = None
    name: str
    teacherId: str
    teacherName: str
    startDate: datetime | None = None
    endDate: datetime | None = None
    examDate: datetime | None = None
    code: str | None = None
    desc: str | None = None
    weeks: list[dict[str, Any]] = Field(default_factory=list)


class CoursePatch(BaseModel):
    key: str | None = None
    name: str | None = None
    teacherId: str | None = None
    teacherName: str | None = None
    startDate: datetime | None = None
    endDate: datetime | None = None
    examDate: datetime | None = None
    code: str | None = None
    desc: str | None = None
    weeks: list[dict[str, Any]] | None = None


class TaskInput(BaseModel):
    sportId: str
    mode: Literal["video", "camera"]
    title: str
    gradingMethod: str = "ai"
    timeLimit: int | None = None
    openTime: datetime | None = None
    closeTime: datetime | None = None
    cameraId: str | None = None


class TaskPatch(BaseModel):
    sportId: str | None = None
    mode: Literal["video", "camera"] | None = None
    title: str | None = None
    gradingMethod: str | None = None
    timeLimit: int | None = None
    openTime: datetime | None = None
    closeTime: datetime | None = None
    cameraId: str | None = None


class EnrollmentInput(BaseModel):
    userId: str


class LiveInput(BaseModel):
    userId: str


class LivePatch(BaseModel):
    completedAt: datetime | None = None
    metrics: dict[str, Any] | None = None
    score: float | None = None


class GradeVideoInput(BaseModel):
    finalScore: float
    teacherComment: str | None = None


class GradeLiveInput(BaseModel):
    score: float
    teacherComment: str | None = None


class CameraInput(BaseModel):
    name: str
    location: str | None = None
    streamUrl: str | None = None
    status: Literal["online", "offline", "error"] = "offline"


class CameraPatch(BaseModel):
    name: str | None = None
    location: str | None = None
    streamUrl: str | None = None
    status: Literal["online", "offline", "error"] | None = None


class APIModel(BaseModel):
    model_config = ConfigDict(extra="allow")
