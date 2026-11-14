from datetime import datetime, timezone
from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, field_serializer
from pydantic.alias_generators import to_camel

from app.models.base import PyObjectId

T = TypeVar("T")


class BaseSchema(BaseModel):
    """Base schema cho tất cả Pydantic schemas, hỗ trợ camelCase và ORM/attributes mode."""

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        arbitrary_types_allowed=True,
        from_attributes=True,
    )

    @field_serializer("*", mode="wrap")
    def _serialize_utc_datetime(self, value: Any, handler):
        # MongoDB trả datetime naive (UTC); gắn tzinfo để JSON có "+00:00" và FE hiển thị đúng giờ địa phương
        if isinstance(value, datetime) and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return handler(value)


class MessageResponse(BaseSchema):
    """Schema response dạng thông báo."""

    message: str
    detail: Optional[str] = None


class PaginatedResponse(BaseSchema, Generic[T]):
    """Schema response hỗ trợ phân trang chuẩn."""

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class ApiResponse(BaseSchema, Generic[T]):
    """Lớp bọc chuẩn hóa dữ liệu đầu ra cho toàn bộ API (Unified Response Envelope)."""

    success: bool = True
    code: int = 200
    message: str = "Thành công"
    data: Optional[T] = None


def success_response(
    data: Any = None,
    message: str = "Thành công",
    code: int = 200,
) -> dict[str, Any]:
    """Helper trả về cấu trúc response chuẩn khi thành công."""
    return {
        "success": True,
        "code": code,
        "message": message,
        "data": data,
    }


def error_response(
    message: str = "Thất bại",
    code: int = 400,
    data: Any = None,
) -> dict[str, Any]:
    """Helper trả về cấu trúc response chuẩn khi có lỗi."""
    return {
        "success": False,
        "code": code,
        "message": message,
        "data": data,
    }
