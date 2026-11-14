"""
Script Migration v1: Nâng cấp và đồng bộ hóa schema cho hệ thống LMS Thể dục AI.
Nhiệm vụ:
1. Chuẩn hóa courses: thêm status, isGradeLocked, allowPracticeSubmission, allowExamSubmission, gradingFormula.
2. Chuẩn hóa tasks: thêm category, isLocked, maxAttempts, gradingMethod.
3. Chuẩn hóa enrollments: denormalize thông tin sinh viên (studentCode, studentName, studentEmail, studentGender), grades struct.
4. Tạo indexes mới trên MongoDB.

Chạy script:
    python scripts/migrate_v1.py
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

# Đảm bảo import được app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bson import ObjectId
from app.core.database import get_db
from app.main import init_db_indexes


def run_migration():
    db = get_db()
    now = datetime.now(timezone.utc)
    print("=" * 60)
    print(">>> BẮT ĐẦU MIGRATION SCHEMA V1")
    print("=" * 60)

    # 1. Cập nhật Courses
    print("\n[1/4] Chuẩn hóa collection 'courses'...")
    course_res = db.courses.update_many(
        {"status": {"$exists": False}},
        {
            "$set": {
                "status": "in_progress",
                "isGradeLocked": False,
                "gradeLockedAt": None,
                "gradeLockedBy": None,
                "allowPracticeSubmission": True,
                "allowExamSubmission": True,
                "gradingFormula": {
                    "attendanceWeight": 0.2,
                    "practiceWeight": 0.3,
                    "examWeight": 0.5,
                },
                "updatedAt": now,
            }
        },
    )
    print(f"  + Đã cập nhật {course_res.modified_count} khóa học.")

    # 2. Cập nhật Tasks
    print("\n[2/4] Chuẩn hóa collection 'tasks'...")
    task_res = db.tasks.update_many(
        {"category": {"$exists": False}},
        {
            "$set": {
                "category": "practice",
                "isLocked": False,
                "maxAttempts": 3,
                "gradingMethod": "highest",
                "updatedAt": now,
            }
        },
    )
    print(f"  + Đã cập nhật {task_res.modified_count} bài tập.")

    # 3. Chuẩn hóa Enrollments (Denormalize từ Users)
    print("\n[3/4] Chuẩn hóa collection 'enrollments' (Denormalization)...")
    enrollments = list(db.enrollments.find({}))
    updated_enr = 0
    for enr in enrollments:
        uid = enr.get("userId")
        user = db.users.find_one({"_id": ObjectId(uid)}) if uid else None

        update_fields = {}
        if user:
            if not enr.get("studentCode"):
                update_fields["studentCode"] = user.get("userCode", "")
            if not enr.get("studentName"):
                update_fields["studentName"] = user.get("name", "")
            if not enr.get("studentEmail"):
                update_fields["studentEmail"] = user.get("email", "")
            if not enr.get("studentGender"):
                update_fields["studentGender"] = user.get("gender", "Nam")

        if not enr.get("grades"):
            update_fields["grades"] = {
                "attendanceScore": None,
                "processScore": None,
                "examScore": None,
                "finalScore": None,
                "letterGrade": None,
                "isPassed": None,
            }
        if "isGradeLocked" not in enr:
            update_fields["isGradeLocked"] = False

        if update_fields:
            update_fields["updatedAt"] = now
            db.enrollments.update_one({"_id": enr["_id"]}, {"$set": update_fields})
            updated_enr += 1

    print(f"  + Đã denormalize thông tin cho {updated_enr} bản ghi ghi danh.")

    # 4. Khởi tạo Indexes mới
    print("\n[4/4] Khởi tạo Compound Indexes mới trên MongoDB...")
    init_db_indexes()
    print("  + Hoàn tất cấu hình chỉ mục.")

    print("\n" + "=" * 60)
    print(">>> MIGRATION V1 THÀNH CÔNG RỰC RỠ!")
    print("=" * 60)


if __name__ == "__main__":
    run_migration()
