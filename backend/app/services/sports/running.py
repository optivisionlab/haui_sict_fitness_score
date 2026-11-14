from typing import Any, Optional
from app.models.sport import SportMode
from .base import MetricSpec, SportDefinition


def calculate_running_score(metrics: dict[str, Any], criteria: Optional[dict[str, Any]] = None) -> float:
    """Tính điểm môn Chạy bộ dựa trên thời gian hoàn thành và điểm kỹ thuật tư thế."""
    duration_sec = metrics.get("durationSec", metrics.get("duration_sec", metrics.get("duration", 400)))
    target_time = (criteria or {}).get("target_time_sec", 360)  # Chuẩn 6 phút

    try:
        duration_sec = float(duration_sec)
    except (ValueError, TypeError):
        duration_sec = 400.0

    if duration_sec <= target_time:
        time_score = 10.0
    else:
        diff = duration_sec - target_time
        time_score = max(10.0 - (diff / 30.0) * 0.5, 3.0)

    form_score = metrics.get("formScore", metrics.get("form_score", 8.0))
    try:
        form_score = float(form_score)
    except (ValueError, TypeError):
        form_score = 8.0

    # 80% thời gian + 20% kỹ thuật/tư thế sải bước
    final_score = time_score * 0.8 + form_score * 0.2
    return round(min(max(final_score, 0.0), 10.0), 2)


def generate_running_comment(metrics: dict[str, Any], score: float) -> str:
    """Nhận xét chi tiết môn Chạy bộ."""
    duration_sec = int(metrics.get("durationSec", metrics.get("duration_sec", metrics.get("duration", 0))))
    mins = duration_sec // 60
    secs = duration_sec % 60
    time_str = f"{mins}p{secs:02d}s" if duration_sec > 0 else "N/A"

    if score >= 8.5:
        return f"Thành tích xuất sắc! Hoàn thành cự ly trong {time_str}. Thể lực và nhịp thở phân phối rất đều."
    elif score >= 7.0:
        return f"Khá tốt! Hoàn thành trong {time_str}. Cần cải thiện sải chân ở đoạn nước rút cuối."
    elif score >= 5.0:
        return f"Đạt chuẩn thể lực. Thời gian: {time_str}. Cần tăng cường luyện tập sức bền hô hấp."
    else:
        return f"Chưa đạt chỉ tiêu thời gian ({time_str}). Đề nghị rèn luyện thêm bài tập chạy chậm tích lũy."


RUNNING_DEFINITION = SportDefinition(
    code="RUNNING",
    name="Chạy bộ",
    mode=SportMode.CAMERA,
    description="Môn chạy bộ/chạy bền rèn luyện thể lực và sức bền tim mạch",
    metrics=[
        MetricSpec(
            name="duration_sec",
            aliases=["durationSec", "duration", "time"],
            type="int",
            required=True,
            description="Tổng thời gian chạy",
            unit="giây",
            default=0,
        ),
        MetricSpec(
            name="distance_meters",
            aliases=["distanceMeters", "distance"],
            type="float",
            required=False,
            description="Quãng đường chạy được",
            unit="m",
            default=0.0,
        ),
        MetricSpec(
            name="avg_pace",
            aliases=["avgPace", "pace", "avgSpeed"],
            type="float",
            required=False,
            description="Tốc độ trung bình (pace hoặc m/s)",
            unit="phút/km",
            default=0.0,
        ),
        MetricSpec(
            name="form_score",
            aliases=["formScore", "postureScore"],
            type="float",
            required=False,
            description="Điểm kỹ thuật dáng chạy do Camera/AI nhận diện",
            unit="điểm",
            default=8.0,
        ),
        MetricSpec(
            name="laps",
            aliases=["lapCount", "lap_count"],
            type="int",
            required=False,
            description="Số vòng sân đã hoàn thành",
            unit="vòng",
            default=0,
        ),
    ],
    thresholds={
        "target_time_sec": 360.0,
        "pass_score": 5.0,
        "excellent_score": 8.5,
    },
    formula_description="80% thời gian hoàn thành so với mốc chuẩn (360s) + 20% điểm kỹ thuật tư thế (formScore)",
    calculate_score_fn=calculate_running_score,
    custom_comment_fn=generate_running_comment,
)
