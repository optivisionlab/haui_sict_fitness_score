from typing import Any, Optional
from app.models.sport import SportMode
from .base import MetricSpec, SportDefinition


def calculate_pickleball_score(metrics: dict[str, Any], criteria: Optional[dict[str, Any]] = None) -> float:
    """
    Tính điểm môn Pickleball:
    - Tỷ lệ đánh trúng bóng (hitRate) chiếm 70%
    - Số lượng cú vung vợt tích cực (swingTotal) chiếm 20%
    - Tỷ lệ bóng vào sân hợp lệ (inCourtRate) chiếm 10%
    """
    hit_rate = metrics.get("hitRate", metrics.get("hit_rate"))
    hit_count = metrics.get("hitCount", metrics.get("hit_count", 0))
    swing_total = metrics.get("swingTotal", metrics.get("swing_total", 0))
    in_court_count = metrics.get("inCourtCount", metrics.get("in_court_count", hit_count))

    try:
        swing_total = float(swing_total)
        hit_count = float(hit_count)
        in_court_count = float(in_court_count)
    except (ValueError, TypeError):
        swing_total, hit_count, in_court_count = 0.0, 0.0, 0.0

    if hit_rate is None and swing_total > 0:
        hit_rate = hit_count / swing_total
    elif hit_rate is None:
        hit_rate = 0.0
    else:
        try:
            hit_rate = float(hit_rate)
            if hit_rate > 1.0:  # nếu là phần trăm (0 - 100)
                hit_rate = hit_rate / 100.0
        except (ValueError, TypeError):
            hit_rate = 0.0

    in_court_rate = (in_court_count / hit_count) if hit_count > 0 else 0.0
    score = (hit_rate * 7.0) + (min(swing_total / 20.0, 1.0) * 2.0) + (in_court_rate * 1.0)
    return round(min(max(score, 0.0), 10.0), 2)


def generate_pickleball_comment(metrics: dict[str, Any], score: float) -> str:
    """Nhận xét chi tiết môn Pickleball."""
    hit_rate = metrics.get("hitRate", metrics.get("hit_rate", 0.0))
    hit_count = int(metrics.get("hitCount", metrics.get("hit_count", 0)))
    swing_total = int(metrics.get("swingTotal", metrics.get("swing_total", 0)))

    try:
        hit_rate_val = float(hit_rate)
        pct = round(hit_rate_val * 100 if hit_rate_val <= 1.0 else hit_rate_val, 1)
    except (ValueError, TypeError):
        pct = 0.0

    if score >= 8.5:
        return f"Kỹ thuật xuất sắc! Tỷ lệ chạm bóng trúng tâm vợt {pct}% ({hit_count}/{swing_total} lần). Động tác mở vợt và đón bóng chuẩn mực."
    elif score >= 7.0:
        return f"Khá tốt! Đạt {hit_count} lần trúng bóng ({pct}%). Cần chú ý giữ trọng tâm thấp khi thực hiện các cú dink và volley."
    elif score >= 5.0:
        return f"Đạt yêu cầu cơ bản. Tỷ lệ trúng bóng {pct}%. Cần rèn luyện thêm cảm giác tiếp xúc bóng ở khu vực Non-Volley Zone (Kitchen)."
    else:
        return f"Chưa đạt yêu cầu (tỷ lệ trúng {pct}%). Đề nghị xem lại video kỹ thuật cầm vợt và tư thế đứng chuẩn bị."


PICKLEBALL_DEFINITION = SportDefinition(
    code="PICKLEBALL",
    name="Pickleball",
    mode=SportMode.VIDEO,
    description="Môn Pickleball đánh giá kỹ thuật vung vợt, tiếp xúc bóng và độ chuẩn xác",
    metrics=[
        MetricSpec(
            name="hit_count",
            aliases=["hitCount", "hits"],
            type="int",
            required=True,
            description="Số lần đánh trúng bóng chuẩn xác",
            unit="lần",
            default=0,
        ),
        MetricSpec(
            name="swing_total",
            aliases=["swingTotal", "swings"],
            type="int",
            required=False,
            description="Tổng số lần vung vợt thực hiện",
            unit="lần",
            default=0,
        ),
        MetricSpec(
            name="hit_rate",
            aliases=["hitRate", "accuracy"],
            type="float",
            required=False,
            description="Tỷ lệ đánh trúng bóng (0.0 - 1.0)",
            unit="%",
            default=0.0,
        ),
        MetricSpec(
            name="in_court_count",
            aliases=["inCourtCount", "in_court"],
            type="int",
            required=False,
            description="Số lần bóng đáp vào trong sân hợp lệ",
            unit="lần",
            default=0,
        ),
        MetricSpec(
            name="shot_type",
            aliases=["shotType"],
            type="str",
            required=False,
            description="Loại cú đánh kỹ thuật (dink, volley, serve, drive)",
            default="general",
        ),
    ],
    thresholds={
        "min_hit_rate": 0.5,
        "min_swings": 10.0,
        "pass_score": 5.0,
        "excellent_score": 8.5,
    },
    formula_description="hitRate * 7.0 + min(swingTotal / 20.0, 1.0) * 2.0 + (inCourtCount / hitCount) * 1.0",
    calculate_score_fn=calculate_pickleball_score,
    custom_comment_fn=generate_pickleball_comment,
)
