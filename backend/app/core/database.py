"""Small, explicit PyMongo repository used by the API routers."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from bson import ObjectId
from pymongo import ASCENDING, MongoClient

from app.core.config import settings

logger = logging.getLogger(__name__)
client = MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=3000)
database = client[settings.MONGODB_DB]


def object_id(value: str) -> ObjectId:
    if not ObjectId.is_valid(value):
        raise ValueError("Invalid MongoDB identifier")
    return ObjectId(value)


def clean(document: dict[str, Any] | None) -> dict[str, Any] | None:
    if document is None:
        return None
    document = dict(document)
    identifier = document.pop("_id", None)
    document["id"] = str(identifier) if identifier is not None else document.get("id")
    return document


def collection(name: str):
    return database[name]


def get_db():
    return database


def now() -> datetime:
    return datetime.utcnow()


def seed_initial_data() -> None:
    from app.core.security import hash_password
    if database.users.count_documents({}) == 0:
        logger.info("Seeding initial users...")
        users = [
            {
                "username": "admin",
                "email": "admin@haui.edu.vn",
                "passwordHash": hash_password("password123"),
                "name": "Quản trị viên Hệ thống",
                "role": "admin",
                "status": "active",
                "createdAt": now(),
                "updatedAt": now(),
            },
            {
                "username": "teacher01",
                "email": "gv001@haui.edu.vn",
                "passwordHash": hash_password("password123"),
                "name": "ThS. Đặng Văn Long",
                "role": "teacher",
                "studentCode": "GV001",
                "status": "active",
                "createdAt": now(),
                "updatedAt": now(),
            },
            {
                "username": "student01",
                "email": "sv2021001@haui.edu.vn",
                "passwordHash": hash_password("password123"),
                "name": "Nguyễn Văn A",
                "role": "student",
                "studentCode": "SV2021001",
                "status": "active",
                "createdAt": now(),
                "updatedAt": now(),
            },
            {
                "username": "student02",
                "email": "sv2021002@haui.edu.vn",
                "passwordHash": hash_password("password123"),
                "name": "Trần Thị Mai",
                "role": "student",
                "studentCode": "SV2021002",
                "status": "active",
                "createdAt": now(),
                "updatedAt": now(),
            },
        ]
        database.users.insert_many(users)

    teacher = database.users.find_one({"role": "teacher"})
    student = database.users.find_one({"role": "student"})

    if database.sports.count_documents({}) == 0:
        logger.info("Seeding initial sports...")
        sports = [
            {"code": "pickleball", "name": "Pickleball", "scoringConfig": {"metricsFields": ["hitRate", "postureScore"], "formula": "0.5 * hitRate + 0.5 * postureScore"}, "createdAt": now(), "updatedAt": now()},
            {"code": "chay", "name": "Điền kinh & Chạy", "scoringConfig": {"metricsFields": ["pace", "postureScore"], "formula": "0.5 * pace + 0.5 * postureScore"}, "createdAt": now(), "updatedAt": now()},
            {"code": "badminton", "name": "Cầu lông", "scoringConfig": {"metricsFields": ["hitRate", "postureScore"], "formula": "0.5 * hitRate + 0.5 * postureScore"}, "createdAt": now(), "updatedAt": now()},
        ]
        database.sports.insert_many(sports)

    pb_sport = database.sports.find_one({"code": "pickleball"})
    run_sport = database.sports.find_one({"code": "chay"})

    if database.courses.count_documents({}) == 0 and teacher and pb_sport and run_sport:
        logger.info("Seeding initial courses and tasks...")
        c1 = {
            "key": "pickleball-k17",
            "name": "Pickleball - Giáo dục Thể chất 1",
            "teacherId": str(teacher["_id"]),
            "teacherName": teacher.get("name", "ThS. Đặng Văn Long"),
            "startDate": datetime(2026, 9, 1),
            "endDate": datetime(2026, 12, 15),
            "examDate": datetime(2026, 11, 20),
            "code": "20261PB0001_TX001",
            "desc": "Học phần trang bị cho sinh viên kỹ thuật cơ bản môn Pickleball. Đánh giá kết quả học tập qua hình thức nộp video thực hành để hệ thống chấm điểm.",
            "studentTotal": 2,
            "createdAt": now(),
            "updatedAt": now(),
        }
        res_c1 = database.courses.insert_one(c1)
        course_id_1 = str(res_c1.inserted_id)

        c2 = {
            "key": "running-k17",
            "name": "Chạy & Điền kinh - Giáo dục Thể chất 2",
            "teacherId": str(teacher["_id"]),
            "teacherName": "ThS. Vũ Thị Lan",
            "startDate": datetime(2026, 9, 1),
            "endDate": datetime(2026, 10, 30),
            "examDate": datetime(2026, 11, 5),
            "code": "20261TD0002_TX001",
            "desc": "Học phần rèn luyện thể lực nền tảng qua các bài chạy bền và chạy tốc độ. Đánh giá kết quả qua video quay lại quá trình thực hiện bài chạy.",
            "studentTotal": 2,
            "createdAt": now(),
            "updatedAt": now(),
        }
        res_c2 = database.courses.insert_one(c2)
        course_id_2 = str(res_c2.inserted_id)

        # Tasks
        tasks = [
            {"courseId": course_id_1, "sportId": str(pb_sport["_id"]), "mode": "video", "title": "Bài thường xuyên 1 (TX1) - Kỹ thuật giao bóng", "gradingMethod": "ai", "timeLimit": 120, "openTime": datetime(2026, 9, 1), "closeTime": datetime(2026, 9, 20), "cameraId": None, "createdAt": now(), "updatedAt": now()},
            {"courseId": course_id_1, "sportId": str(pb_sport["_id"]), "mode": "video", "title": "Bài thường xuyên 2 (TX2) - Kỹ thuật đỡ bóng & di chuyển", "gradingMethod": "ai", "timeLimit": 120, "openTime": datetime(2026, 9, 10), "closeTime": datetime(2026, 9, 30), "cameraId": None, "createdAt": now(), "updatedAt": now()},
            {"courseId": course_id_1, "sportId": str(pb_sport["_id"]), "mode": "video", "title": "Bài giữa kỳ - Phối hợp đánh đôi & chiến thuật", "gradingMethod": "ai", "timeLimit": 120, "openTime": datetime(2026, 10, 1), "closeTime": datetime(2026, 10, 20), "cameraId": None, "createdAt": now(), "updatedAt": now()},
            {"courseId": course_id_1, "sportId": str(pb_sport["_id"]), "mode": "video", "title": "Bài cuối kỳ - Thi đấu tính điểm chính thức", "gradingMethod": "ai", "timeLimit": 120, "openTime": datetime(2026, 11, 1), "closeTime": datetime(2026, 11, 20), "cameraId": None, "createdAt": now(), "updatedAt": now()},
            {"courseId": course_id_2, "sportId": str(run_sport["_id"]), "mode": "video", "title": "Bài thường xuyên 1 (TX1) - Chạy cự ly ngắn (60m - 100m)", "gradingMethod": "ai", "timeLimit": 120, "openTime": datetime(2026, 9, 1), "closeTime": datetime(2026, 9, 15), "cameraId": None, "createdAt": now(), "updatedAt": now()},
            {"courseId": course_id_2, "sportId": str(run_sport["_id"]), "mode": "video", "title": "Bài thường xuyên 2 (TX2) - Chạy bền 1500m", "gradingMethod": "ai", "timeLimit": 120, "openTime": datetime(2026, 9, 16), "closeTime": datetime(2026, 9, 30), "cameraId": None, "createdAt": now(), "updatedAt": now()},
        ]
        res_tasks = database.tasks.insert_many(tasks)
        task_ids = [str(t_id) for t_id in res_tasks.inserted_ids]

        if student:
            student_id = str(student["_id"])
            database.enrollments.insert_many([
                {
                    "courseId": course_id_1,
                    "userId": student_id,
                    "status": "active",
                    "progressPercent": 50.0,
                    "completedTaskIds": [task_ids[0]],
                    "taskScores": {task_ids[0]: 8.5},
                    "grades": {"attendanceScore": 9.0, "processScore": 8.5, "examScore": None, "finalScore": 8.5, "letterGrade": "A", "isPassed": True},
                    "createdAt": now(),
                },
                {
                    "courseId": course_id_2,
                    "userId": student_id,
                    "status": "active",
                    "progressPercent": 75.0,
                    "completedTaskIds": [task_ids[4]],
                    "taskScores": {task_ids[4]: 9.0},
                    "grades": {"attendanceScore": 9.5, "processScore": 9.0, "examScore": None, "finalScore": 9.0, "letterGrade": "A+", "isPassed": True},
                    "createdAt": now(),
                },
            ])


def init_db() -> None:
    database.users.create_index("email", unique=True, sparse=True)
    database.users.create_index("username", unique=True, sparse=True)
    database.sports.create_index("code", unique=True)
    database.enrollments.create_index([("courseId", ASCENDING), ("userId", ASCENDING)], unique=True)
    logger.info("MongoDB indexes initialized for %s", settings.MONGODB_DB)
    try:
        seed_initial_data()
    except Exception:
        logger.exception("Initial database seeding failed")
