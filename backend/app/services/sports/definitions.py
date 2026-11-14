from typing import Optional

from .base import (
    BaseSportEvaluator,
    CommentRule,
    ConfigurableSportEvaluator,
    MetricSpec,
    SportDefinition,
)
from .pickleball import PICKLEBALL_DEFINITION
from .running import RUNNING_DEFINITION

# ==============================================================================
# TỪ ĐIỂN TẬP HỢP CÁC MÔN THỂ THAO
# Khi thêm môn mới: tạo file <môn>.py kế thừa/khai báo SportDefinition,
# rồi import và thêm vào từ điển SPORT_DEFINITIONS dưới đây.
# ==============================================================================

SPORT_DEFINITIONS: dict[str, SportDefinition] = {
    "RUNNING": RUNNING_DEFINITION,
    "PICKLEBALL": PICKLEBALL_DEFINITION,
}


def get_sport_definition(code_or_name: Optional[str]) -> Optional[SportDefinition]:
    """Tìm định nghĩa môn thể thao theo mã code hoặc từ khóa tên tiếng Việt."""
    if not code_or_name:
        return None

    key = str(code_or_name).strip().upper()

    # 1. Tìm chính xác theo code
    if key in SPORT_DEFINITIONS:
        return SPORT_DEFINITIONS[key]

    # 2. Tìm mờ theo từ khóa
    if "PICKLE" in key:
        return SPORT_DEFINITIONS.get("PICKLEBALL")
    if "RUN" in key or "CHAY" in key or "CHẠY" in key:
        return SPORT_DEFINITIONS.get("RUNNING")

    return None


def list_sport_definitions() -> list[SportDefinition]:
    """Lấy danh sách tất cả các định nghĩa môn thể thao trong hệ thống."""
    return list(SPORT_DEFINITIONS.values())


__all__ = [
    "MetricSpec",
    "CommentRule",
    "SportDefinition",
    "ConfigurableSportEvaluator",
    "BaseSportEvaluator",
    "SPORT_DEFINITIONS",
    "get_sport_definition",
    "list_sport_definitions",
    "RUNNING_DEFINITION",
    "PICKLEBALL_DEFINITION",
]
