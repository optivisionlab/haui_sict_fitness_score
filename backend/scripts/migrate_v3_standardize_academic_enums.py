"""
Migration v3: Chuẩn hóa toàn bộ trường Học kỳ (Semester) và Bộ môn (Sport) theo Master Enums.
Loại bỏ triệt để các chuỗi rác như 'chayben-01' hay 'pickleball-01' gán nhầm vào semester.
An toàn khi chạy nhiều lần (Idempotent).

Cách chạy:
    python scripts/migrate_v3_standardize_academic_enums.py
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Đảm bảo import được backend app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import get_db
from app.core.enums import (
    PhysicalSubjectCode,
    PHYSICAL_SUBJECTS_MAP,
    deduce_sport_metadata,
    format_semester_info,
    parse_semester_code,
)


def run_migration():
    db = get_db()
    print("=" * 70)
    print(">>> BẮT ĐẦU MIGRATION V3: CHUẨN HÓA ACADEMIC ENUMS (SEMESTER & SPORT)")
    print("=" * 70)

    # 1. Lấy danh sách sport documents trong collection sports
    sports_by_code = {}
    for s in db.sports.find():
        code = (s.get("code") or "").upper()
        sports_by_code[code] = s

    courses = list(db.courses.find())
    print(f"Tìm thấy {len(courses)} lớp học phần trong collection 'courses'.\n")

    updated_count = 0
    now = datetime.now(timezone.utc)

    for c in courses:
        cid = c["_id"]
        c_name = c.get("name", "")
        c_code = c.get("code", "")
        c_key = c.get("key", "")
        current_sem = str(c.get("semester") or "").strip()
        current_sport_code = str(c.get("sportCode") or "").strip().upper()

        update_set = {}

        # -------------------------------------------------------------
        # 1. Chuẩn hóa Môn thể chất (Sport)
        # -------------------------------------------------------------
        target_sport_code = current_sport_code
        if not target_sport_code or target_sport_code not in PHYSICAL_SUBJECTS_MAP:
            meta = deduce_sport_metadata(c_name, c_code or c_key)
            target_sport_code = meta.code.value
            update_set["sportCode"] = target_sport_code
            update_set["sportName"] = meta.name
        else:
            meta = PHYSICAL_SUBJECTS_MAP[PhysicalSubjectCode(target_sport_code)]
            if c.get("sportName") != meta.name:
                update_set["sportName"] = meta.name

        # Liên kết với _id của collection sports nếu có
        if not c.get("sportId") or c.get("sportId") == "None":
            if target_sport_code in sports_by_code:
                update_set["sportId"] = str(sports_by_code[target_sport_code]["_id"])

        # -------------------------------------------------------------
        # 2. Chuẩn hóa Học kỳ (Semester)
        # -------------------------------------------------------------
        sem_info = parse_semester_code(current_sem)
        # Nếu semester đang chứa chuỗi rác như "chayben-01", "pickleball-01" hoặc None
        if not sem_info or current_sem in ["chayben-01", "pickleball-01"]:
            # Phân tích theo start_date hoặc mặc định 2026-2027.1
            start_date = c.get("startDate")
            year = "2026-2027"
            term = 1
            if start_date and hasattr(start_date, "month"):
                m = start_date.month
                y = start_date.year
                if m >= 8:
                    year = f"{y}-{y+1}"
                    term = 1
                elif m <= 5:
                    year = f"{y-1}-{y}"
                    term = 2
                else:
                    year = f"{y-1}-{y}"
                    term = 3

            sem_info = format_semester_info(year, term)
            update_set["semester"] = sem_info.code
            update_set["semesterName"] = sem_info.name
            update_set["academicYear"] = sem_info.academic_year
            update_set["term"] = sem_info.term
        else:
            # Đồng bộ lại semesterName theo chuẩn
            expected_name = sem_info.name
            if c.get("semesterName") != expected_name:
                update_set["semesterName"] = expected_name
            if not c.get("academicYear"):
                update_set["academicYear"] = sem_info.academic_year
            if not c.get("term"):
                update_set["term"] = sem_info.term

        if update_set:
            update_set["updatedAt"] = now
            db.courses.update_one({"_id": cid}, {"$set": update_set})
            updated_count += 1
            print(f"  [UPDATED] Course '{c_name}' (ID: {cid}):")
            for k, v in update_set.items():
                if k != "updatedAt":
                    print(f"      -> {k}: {v}")

    print("\n" + "=" * 70)
    print(f">>> HOÀN TẤT: Đã chuẩn hóa {updated_count}/{len(courses)} lớp học phần.")
    print("=" * 70)


if __name__ == "__main__":
    run_migration()
