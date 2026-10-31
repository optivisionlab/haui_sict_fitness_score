"""
Migration v2: Cập nhật các trường môn học (sport) và học kỳ (semester) cho collection courses.
An toàn khi chạy nhiều lần (idempotent).
Chạy lệnh:
    python scripts/migrate_v2_course_fields.py
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

# Đảm bảo import được backend app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import get_db


def deduce_sport_from_name(course_name: str, code: str = ""):
    """Suy luận môn thể thao từ tên hoặc mã lớp học."""
    name_lower = (course_name or "").lower()
    code_lower = (code or "").lower()

    if "pickleball" in name_lower or "pb" in code_lower:
        return "Pickleball", "PICKLEBALL"
    elif "điền kinh" in name_lower or "chạy" in name_lower or "run" in code_lower or "cb" in code_lower:
        return "Điền kinh", "RUNNING"
    elif "bóng đá" in name_lower or "đá bóng" in name_lower or "football" in name_lower:
        return "Bóng đá", "FOOTBALL"
    elif "cầu lông" in name_lower or "badminton" in name_lower:
        return "Cầu lông", "BADMINTON"
    elif "bóng rổ" in name_lower or "basketball" in name_lower:
        return "Bóng rổ", "BASKETBALL"
    elif "bóng chuyền" in name_lower or "volleyball" in name_lower:
        return "Bóng chuyền", "VOLLEYBALL"
    elif "bơi" in name_lower or "swim" in name_lower:
        return "Bơi lội", "SWIMMING"
    return "Giáo dục Thể chất", "GENERAL"


def deduce_semester_from_date_or_key(key: str = "", start_date: datetime = None):
    """Suy luận thông tin học kỳ."""
    # Nếu key có định dạng 2025-2026.1 hoặc 2026-2027.1
    if key and "." in key:
        parts = key.split(".", 1)
        year = parts[0]
        try:
            term = int(parts[1])
        except ValueError:
            term = 1
        term_labels = {1: "Học kỳ 1", 2: "Học kỳ 2", 3: "Học kỳ hè"}
        t_name = term_labels.get(term, f"Học kỳ {term}")
        return key, f"{t_name} ({year.replace('-', ' - ')})", year, term

    # Mặc định theo ngày bắt đầu (nếu có 2026) hoặc năm hiện tại
    year = "2026-2027"
    term = 1
    if start_date:
        month = start_date.month
        y = start_date.year
        if month >= 8:
            year = f"{y}-{y+1}"
            term = 1
        elif month <= 5:
            year = f"{y-1}-{y}"
            term = 2
        else:
            year = f"{y-1}-{y}"
            term = 3

    term_labels = {1: "Học kỳ 1", 2: "Học kỳ 2", 3: "Học kỳ hè"}
    sem_code = f"{year}.{term}"
    sem_name = f"{term_labels.get(term, 'Học kỳ')} ({year.replace('-', ' - ')})"
    return sem_code, sem_name, year, term


def run_migration():
    db = get_db()
    print("=" * 60)
    print(">>> BẮT ĐẦU MIGRATION V2: SPORT & SEMESTER FIELDS CHO COURSES")
    print("=" * 60)

    # Lấy danh sách sports có trong DB
    sports_map = {}
    for s in db.sports.find():
        code = (s.get("code") or "").upper()
        sports_map[code] = s

    courses = list(db.courses.find())
    print(f"Tìm thấy {len(courses)} lớp học phần trong collection 'courses'.")

    updated_count = 0
    for c in courses:
        cid = c["_id"]
        c_name = c.get("name", "")
        c_code = c.get("code", "")
        c_key = c.get("key", "")
        c_start = c.get("startDate")

        update_set = {}

        # 1. Sport fields
        if not c.get("sportId") or not c.get("sportName"):
            # Kiểm tra task đầu tiên của course
            first_task = db.tasks.find_one({"courseId": str(cid)})
            if first_task and first_task.get("sportId"):
                s_doc = db.sports.find_one({"_id": first_task["sportId"]})
                if s_doc:
                    update_set["sportId"] = str(s_doc["_id"])
                    update_set["sportName"] = s_doc.get("name", "")
                    update_set["sportCode"] = (s_doc.get("code") or "").upper()

            if "sportId" not in update_set:
                s_name, s_code = deduce_sport_from_name(c_name, c_code)
                update_set["sportName"] = s_name
                update_set["sportCode"] = s_code
                if s_code in sports_map:
                    update_set["sportId"] = str(sports_map[s_code]["_id"])

        # 2. Semester fields
        if not c.get("semester") or not c.get("semesterName"):
            sem_code, sem_name, sem_year, sem_term = deduce_semester_from_date_or_key(c_key, c_start)
            update_set["semester"] = sem_code
            update_set["semesterName"] = sem_name
            update_set["academicYear"] = sem_year
            update_set["term"] = sem_term

        if update_set:
            update_set["updatedAt"] = datetime.now(timezone.utc)
            db.courses.update_one({"_id": cid}, {"$set": update_set})
            updated_count += 1
            print(f"  + Đã cập nhật lớp '{c_name}': {update_set}")

    print("=" * 60)
    print(f">>> HOÀN TẤT: Đã cập nhật {updated_count}/{len(courses)} lớp học phần.")
    print("=" * 60)


if __name__ == "__main__":
    run_migration()
