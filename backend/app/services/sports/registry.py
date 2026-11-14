import logging
from typing import Any, Optional

from .base import BaseSportEvaluator
from .definitions import SPORT_DEFINITIONS, get_sport_definition

logger = logging.getLogger(__name__)


class DefaultSportEvaluator(BaseSportEvaluator):
    """Bộ đánh giá dự phòng chung khi chưa có evaluator chuyên biệt cho môn thể thao mới."""

    @property
    def sport_code(self) -> str:
        return "DEFAULT"

    @property
    def sport_name(self) -> str:
        return "Môn Thể Thao Mặc Định"

    def validate_metrics(self, metrics: dict[str, Any]) -> tuple[bool, Optional[str]]:
        return True, None

    def calculate_score(
        self, metrics: dict[str, Any], criteria: Optional[dict[str, Any]] = None
    ) -> float:
        # Nếu có điểm trực tiếp trong metrics thì ưu tiên lấy, ngược lại mặc định 7.0
        raw_score = metrics.get("score", metrics.get("aiScore", metrics.get("ai_score", 7.0)))
        try:
            return round(min(max(float(raw_score), 0.0), 10.0), 2)
        except Exception:
            return 7.0

    def generate_comment(self, metrics: dict[str, Any], score: float) -> str:
        if score >= 8.5:
            return "Kỹ thuật thực hiện xuất sắc, đạt chuẩn bài tập."
        elif score >= 6.5:
            return "Hoàn thành tốt bài tập, cần rèn luyện thêm để nâng cao thành tích."
        else:
            return "Đã hoàn thành lượt nộp bài, đề nghị cải thiện kỹ thuật động tác."


class SportEvaluatorRegistry:
    """
    Registry quản lý các bộ đánh giá môn thể thao.
    Tất cả các môn được định nghĩa trong `definitions.py` (SPORT_DEFINITIONS)
    sẽ được tự động nạp vào đây khi hệ thống khởi chạy.
    """

    def __init__(self):
        self._evaluators: dict[str, BaseSportEvaluator] = {}
        self._default_evaluator = DefaultSportEvaluator()

        # Tự động nạp toàn bộ môn từ SPORT_DEFINITIONS
        self.load_from_definitions()

    def load_from_definitions(self) -> None:
        """Nạp tất cả evaluators từ SPORT_DEFINITIONS."""
        for definition in SPORT_DEFINITIONS.values():
            self.register(definition.to_evaluator())

    def register(self, evaluator: BaseSportEvaluator) -> None:
        key = evaluator.sport_code.strip().upper()
        self._evaluators[key] = evaluator
        logger.info("Registered sport evaluator for: %s", key)

    def get_evaluator(self, sport_code_or_name: Optional[str]) -> BaseSportEvaluator:
        if not sport_code_or_name:
            return self._default_evaluator

        key = str(sport_code_or_name).strip().upper()
        # 1. Tìm match chính xác
        if key in self._evaluators:
            return self._evaluators[key]

        # 2. Tìm qua helper get_sport_definition (hỗ trợ match mờ / tiếng Việt / alias)
        matched_def = get_sport_definition(sport_code_or_name)
        if matched_def and matched_def.code in self._evaluators:
            return self._evaluators[matched_def.code]

        return self._default_evaluator


# Singleton instance toàn hệ thống
sport_registry = SportEvaluatorRegistry()
