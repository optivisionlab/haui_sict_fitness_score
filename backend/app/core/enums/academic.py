from enum import Enum
from typing import Optional, NamedTuple
from pydantic import BaseModel


class SemesterTerm(int, Enum):
    """Định danh học kỳ chính quy & hè."""
    TERM_1 = 1      # Học kỳ 1 (Thu - Đông)
    TERM_2 = 2      # Học kỳ 2 (Xuân - Hè)
    SUMMER = 3      # Học kỳ phụ / Hè


class PhysicalSubjectCode(str, Enum):
    """Mã định danh chuẩn các môn thể chất tại HaUI."""
    PICKLEBALL = "PICKLEBALL"
    RUNNING = "RUNNING"
    FOOTBALL = "FOOTBALL"
    BADMINTON = "BADMINTON"
    BASKETBALL = "BASKETBALL"
    VOLLEYBALL = "VOLLEYBALL"
    SWIMMING = "SWIMMING"
    GENERAL = "GENERAL"


class PhysicalSubjectMeta(BaseModel):
    code: PhysicalSubjectCode
    name: str              # Tên chuẩn hiển thị (VD: "Pickleball", "Điền kinh")
    course_prefix: str     # Tiền tố mã lớp (VD: "GDTC-PB", "GDTC-CB")
    default_mode: str      # "video" | "camera"


PHYSICAL_SUBJECTS_MAP: dict[PhysicalSubjectCode, PhysicalSubjectMeta] = {
    PhysicalSubjectCode.PICKLEBALL: PhysicalSubjectMeta(
        code=PhysicalSubjectCode.PICKLEBALL,
        name="Pickleball",
        course_prefix="GDTC-PB",
        default_mode="video",
    ),
    PhysicalSubjectCode.RUNNING: PhysicalSubjectMeta(
        code=PhysicalSubjectCode.RUNNING,
        name="Điền kinh",
        course_prefix="GDTC-CB",
        default_mode="camera",
    ),
    PhysicalSubjectCode.FOOTBALL: PhysicalSubjectMeta(
        code=PhysicalSubjectCode.FOOTBALL,
        name="Bóng đá",
        course_prefix="GDTC-FB",
        default_mode="video",
    ),
    PhysicalSubjectCode.BADMINTON: PhysicalSubjectMeta(
        code=PhysicalSubjectCode.BADMINTON,
        name="Cầu lông",
        course_prefix="GDTC-CL",
        default_mode="video",
    ),
    PhysicalSubjectCode.BASKETBALL: PhysicalSubjectMeta(
        code=PhysicalSubjectCode.BASKETBALL,
        name="Bóng rổ",
        course_prefix="GDTC-BR",
        default_mode="video",
    ),
    PhysicalSubjectCode.VOLLEYBALL: PhysicalSubjectMeta(
        code=PhysicalSubjectCode.VOLLEYBALL,
        name="Bóng chuyền",
        course_prefix="GDTC-BC",
        default_mode="video",
    ),
    PhysicalSubjectCode.SWIMMING: PhysicalSubjectMeta(
        code=PhysicalSubjectCode.SWIMMING,
        name="Bơi lội",
        course_prefix="GDTC-BL",
        default_mode="video",
    ),
    PhysicalSubjectCode.GENERAL: PhysicalSubjectMeta(
        code=PhysicalSubjectCode.GENERAL,
        name="Giáo dục Thể chất",
        course_prefix="GDTC",
        default_mode="video",
    ),
}


class AcademicSemesterInfo(NamedTuple):
    code: str              # "2026-2027.1"
    name: str              # "Học kỳ 1 (2026 - 2027)"
    academic_year: str     # "2026-2027"
    term: int              # 1


def format_semester_info(academic_year: str, term: int) -> AcademicSemesterInfo:
    """Đảm bảo chuỗi học kỳ luôn tuân thủ đúng format chuẩn: YYYY-YYYY.T."""
    term_labels = {1: "Học kỳ 1", 2: "Học kỳ 2", 3: "Học kỳ hè"}
    term_text = term_labels.get(term, f"Học kỳ {term}")
    clean_year = academic_year.strip().replace(" - ", "-")
    code = f"{clean_year}.{term}"
    name = f"{term_text} ({clean_year.replace('-', ' - ')})"
    return AcademicSemesterInfo(code=code, name=name, academic_year=clean_year, term=term)


def parse_semester_code(raw: Optional[str]) -> Optional[AcademicSemesterInfo]:
    """Phân tích và validate mã kỳ học."""
    if not raw or not isinstance(raw, str):
        return None
    s = raw.strip()
    if "." in s:
        parts = s.split(".", 1)
        year = parts[0]
        try:
            term = int(parts[1])
            return format_semester_info(year, term)
        except ValueError:
            pass
    return None


def deduce_sport_metadata(name: str = "", code: str = "") -> PhysicalSubjectMeta:
    """Suy luận môn thể thao sang PhysicalSubjectMeta chuẩn."""
    nl = (name or "").lower()
    cl = (code or "").lower()
    if "pickleball" in nl or "pb" in cl:
        return PHYSICAL_SUBJECTS_MAP[PhysicalSubjectCode.PICKLEBALL]
    if "điền kinh" in nl or "chạy" in nl or "run" in cl or "cb" in cl:
        return PHYSICAL_SUBJECTS_MAP[PhysicalSubjectCode.RUNNING]
    if "bóng đá" in nl or "đá bóng" in nl or "football" in nl or "fb" in cl:
        return PHYSICAL_SUBJECTS_MAP[PhysicalSubjectCode.FOOTBALL]
    if "cầu lông" in nl or "badminton" in nl or "cl" in cl:
        return PHYSICAL_SUBJECTS_MAP[PhysicalSubjectCode.BADMINTON]
    if "bóng rổ" in nl or "basketball" in nl or "br" in cl:
        return PHYSICAL_SUBJECTS_MAP[PhysicalSubjectCode.BASKETBALL]
    if "bóng chuyền" in nl or "volleyball" in nl or "bc" in cl:
        return PHYSICAL_SUBJECTS_MAP[PhysicalSubjectCode.VOLLEYBALL]
    if "bơi" in nl or "swim" in nl or "bl" in cl:
        return PHYSICAL_SUBJECTS_MAP[PhysicalSubjectCode.SWIMMING]
    return PHYSICAL_SUBJECTS_MAP[PhysicalSubjectCode.GENERAL]
