from abc import ABC, abstractmethod
from typing import Any, Callable, Optional
from pydantic import BaseModel, Field

from app.models.sport import ScoringConfig, SportMode


class BaseSportEvaluator(ABC):
    """
    Interface cơ sở cho các bộ đánh giá điểm theo từng môn thể thao cụ thể.
    """

    @property
    @abstractmethod
    def sport_code(self) -> str:
        """Mã định danh môn thể thao (e.g. RUNNING, PICKLEBALL)."""
        pass

    @property
    @abstractmethod
    def sport_name(self) -> str:
        """Tên hiển thị tiếng Việt của môn thể thao."""
        pass

    @abstractmethod
    def validate_metrics(self, metrics: dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Kiểm tra tính hợp lệ của cấu trúc metrics do AI Worker gửi về.
        Trả về (is_valid, error_message).
        """
        pass

    @abstractmethod
    def calculate_score(
        self, metrics: dict[str, Any], criteria: Optional[dict[str, Any]] = None
    ) -> float:
        """
        Tính toán điểm số hệ 10 từ các chỉ số kỹ thuật AI đo đạc được.
        """
        pass

    @abstractmethod
    def generate_comment(
        self, metrics: dict[str, Any], score: float
    ) -> str:
        """
        Sinh nhận xét phân tích kỹ thuật tự động cho sinh viên.
        """
        pass


class MetricSpec(BaseModel):
    """
    Quy định chi tiết cho một trường chỉ số đo lường (metric) của môn thể thao.
    """
    name: str = Field(..., description="Tên trường chuẩn (snake_case)")
    aliases: list[str] = Field(default_factory=list, description="Các tên thay thế (camelCase hoặc cách gọi khác từ AI)")
    type: str = Field(default="float", description="Kiểu dữ liệu: 'int', 'float', 'str', 'bool'")
    required: bool = Field(default=False, description="Trường này có bắt buộc AI phải trả về không")
    description: str = Field(default="", description="Mô tả ý nghĩa của chỉ số")
    unit: Optional[str] = Field(default=None, description="Đơn vị đo lường (e.g. 'giây', 'm', 'lần', '%')")
    default: Optional[Any] = Field(default=None, description="Giá trị mặc định nếu không có trong kết quả")

    def extract_value(self, metrics: dict[str, Any]) -> Any:
        """Trích xuất giá trị từ dict metrics dựa trên name hoặc các aliases."""
        if not isinstance(metrics, dict):
            return self.default

        # 1. Tìm theo tên chính xác
        if self.name in metrics and metrics[self.name] is not None:
            return metrics[self.name]

        # 2. Tìm qua các aliases
        for alias in self.aliases:
            if alias in metrics and metrics[alias] is not None:
                return metrics[alias]

        return self.default


class CommentRule(BaseModel):
    """
    Quy định sinh nhận xét tự động theo mốc điểm.
    """
    min_score: float = Field(..., description="Ngưỡng điểm tối thiểu để áp dụng nhận xét này (hệ 10)")
    template: str = Field(..., description="Mẫu nhận xét, hỗ trợ format {biến}")


class SportDefinition:
    """
    Định nghĩa toàn diện cho một môn thể thao trong hệ thống.
    """

    def __init__(
        self,
        code: str,
        name: str,
        mode: SportMode,
        description: str = "",
        metrics: Optional[list[MetricSpec]] = None,
        thresholds: Optional[dict[str, float]] = None,
        formula_description: Optional[str] = None,
        calculate_score_fn: Optional[Callable[[dict[str, Any], Optional[dict[str, Any]]], float]] = None,
        comment_rules: Optional[list[CommentRule]] = None,
        custom_comment_fn: Optional[Callable[[dict[str, Any], float], str]] = None,
    ):
        self.code = code.strip().upper()
        self.name = name.strip()
        self.mode = mode
        self.description = description
        self.metrics = metrics or []
        self.thresholds = thresholds or {}
        self.formula_description = formula_description
        self.calculate_score_fn = calculate_score_fn
        self.comment_rules = sorted(
            comment_rules or [], key=lambda r: r.min_score, reverse=True
        )
        self.custom_comment_fn = custom_comment_fn

    def get_metric_spec(self, name_or_alias: str) -> Optional[MetricSpec]:
        """Tìm đặc tả chỉ số theo tên hoặc alias."""
        for m in self.metrics:
            if m.name == name_or_alias or name_or_alias in m.aliases:
                return m
        return None

    def get_all_metric_keys(self) -> list[str]:
        """Lấy danh sách các trường metrics (bao gồm cả alias)."""
        keys = []
        for m in self.metrics:
            keys.append(m.name)
            keys.extend(m.aliases)
        return keys

    def to_scoring_config(self) -> ScoringConfig:
        """Chuyển đổi thành model ScoringConfig để lưu trữ trong database."""
        return ScoringConfig(
            metrics_fields=[m.name for m in self.metrics],
            formula=self.formula_description,
            thresholds=self.thresholds,
        )

    def to_evaluator(self) -> BaseSportEvaluator:
        """Tạo instance Evaluator tương thích BaseSportEvaluator."""
        return ConfigurableSportEvaluator(self)

    def to_dict(self) -> dict[str, Any]:
        """Xuất thông tin định nghĩa dạng dictionary phục vụ API / frontend."""
        return {
            "code": self.code,
            "name": self.name,
            "mode": self.mode.value,
            "description": self.description,
            "metrics": [m.model_dump() for m in self.metrics],
            "thresholds": self.thresholds,
            "formulaDescription": self.formula_description,
            "commentRules": [r.model_dump() for r in self.comment_rules],
        }


class ConfigurableSportEvaluator(BaseSportEvaluator):
    """
    Evaluator được cấu hình động dựa trên SportDefinition.
    """

    def __init__(self, definition: SportDefinition):
        self.definition = definition

    @property
    def sport_code(self) -> str:
        return self.definition.code

    @property
    def sport_name(self) -> str:
        return self.definition.name

    def validate_metrics(self, metrics: dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Kiểm tra các trường bắt buộc đã được định nghĩa trong metrics."""
        if not isinstance(metrics, dict):
            return False, "Metrics phải là một đối tượng dictionary"

        for spec in self.definition.metrics:
            if spec.required:
                val = spec.extract_value(metrics)
                if val is None:
                    return False, f"Thiếu trường bắt buộc '{spec.name}' trong metrics môn {self.sport_name}"

        return True, None

    def calculate_score(
        self, metrics: dict[str, Any], criteria: Optional[dict[str, Any]] = None
    ) -> float:
        """Tính điểm dựa trên hàm tính điểm được cấu hình hoặc fallback."""
        if self.definition.calculate_score_fn:
            try:
                score = self.definition.calculate_score_fn(metrics, criteria)
                return round(min(max(float(score), 0.0), 10.0), 2)
            except Exception:
                pass

        # Fallback: Nếu AI Worker đã gửi sẵn score / aiScore
        for k in ["score", "aiScore", "ai_score", "finalScore", "final_score"]:
            if k in metrics and metrics[k] is not None:
                try:
                    return round(min(max(float(metrics[k]), 0.0), 10.0), 2)
                except (ValueError, TypeError):
                    pass

        return 7.0

    def generate_comment(self, metrics: dict[str, Any], score: float) -> str:
        """Sinh nhận xét tự động theo hàm custom hoặc bảng quy tắc CommentRule."""
        if self.definition.custom_comment_fn:
            try:
                return self.definition.custom_comment_fn(metrics, score)
            except Exception:
                pass

        format_context: dict[str, Any] = {"score": score}
        for spec in self.definition.metrics:
            val = spec.extract_value(metrics)
            format_context[spec.name] = val if val is not None else 0
            for alias in spec.aliases:
                format_context[alias] = format_context[spec.name]

        for rule in self.definition.comment_rules:
            if score >= rule.min_score:
                try:
                    return rule.template.format(**format_context)
                except Exception:
                    return rule.template

        if score >= 5.0:
            return f"Hoàn thành bài tập {self.sport_name}, đạt yêu cầu cơ bản."
        return f"Chưa đạt yêu cầu môn {self.sport_name}. Cần luyện tập thêm để nâng cao thành tích."
