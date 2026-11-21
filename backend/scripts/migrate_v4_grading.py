"""Migration v4: chuẩn hóa cấu trúc điểm học phần thể chất.

- Gán `kind` cho bài kiểm tra cũ (regular / midterm / final) dựa trên category và tiêu đề.
- Đặt tỷ trọng mặc định 0.1 / 0.3 / 0.6 và điều kiện dự thi mặc định cho lớp chưa cấu hình
  (lớp đã có tỷ trọng khác mặc định cũ 0.2 / 0.3 / 0.5 được giữ nguyên).
- Tính lại điểm toàn bộ sinh viên theo quy tắc mới (điểm giữa kỳ vào quá trình, điểm thi = cuối kỳ).

Chạy (idempotent, chạy lại nhiều lần không sao):
    python scripts/migrate_v4_grading.py            # xem trước, không ghi
    python scripts/migrate_v4_grading.py --apply    # ghi vào database
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import get_db  # noqa: E402
from app.crud.task import crud_task  # noqa: E402
from app.models.task import task_kind  # noqa: E402

OLD_DEFAULT = {"attendanceWeight": 0.2, "practiceWeight": 0.3, "examWeight": 0.5}
NEW_FORMULA = {"attendanceWeight": 0.1, "practiceWeight": 0.3, "examWeight": 0.6}
NEW_ELIGIBILITY = {"enabled": True, "minAttendanceScore": 5.0, "minProcessScore": 4.0}


def main(apply: bool) -> None:
    db = get_db()

    for doc in db.tasks.find({"kind": {"$exists": False}}):
        kind = task_kind(crud_task.model.model_validate(doc)).value
        print(f"task  {doc['_id']}  {doc.get('title', '')[:45]:45}  -> kind={kind}")
        if apply:
            db.tasks.update_one({"_id": doc["_id"]}, {"$set": {"kind": kind}})

    for course in db.courses.find():
        formula = course.get("gradingFormula") or {}
        current = {k: formula.get(k) for k in OLD_DEFAULT}
        update = {}
        if not formula or current == OLD_DEFAULT:
            update["gradingFormula"] = NEW_FORMULA
        if "examEligibility" not in course:
            update["examEligibility"] = NEW_ELIGIBILITY
        if update:
            print(f"course {course.get('code')}: {update}")
            if apply:
                db.courses.update_one({"_id": course["_id"]}, {"$set": update})

    if apply:
        from app.services.grade_calculator import recalculate_course
        for course in db.courses.find({}, {"code": 1, "isGradeLocked": 1}):
            if course.get("isGradeLocked"):
                print(f"course {course.get('code')}: đã chốt điểm, không tính lại")
                continue
            n = recalculate_course(str(course["_id"]))
            print(f"course {course.get('code')}: tính lại điểm {n} sinh viên")
    else:
        print("\nChế độ xem trước. Thêm --apply để ghi vào database.")


if __name__ == "__main__":
    main(apply="--apply" in sys.argv)
