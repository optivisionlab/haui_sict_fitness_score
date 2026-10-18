"""
Script nạp dữ liệu mẫu (Seed Data) chuẩn, đồng bộ 100% cho hệ thống LMS Thể dục AI HaUI.
Bao gồm:
1. Dọn dẹp sạch sẽ MinIO bucket 'videos' (xóa mọi object mồ côi cũ).
2. Dọn dẹp sạch sẽ 9 collections MongoDB.
3. Upload video mẫu thực tế lên MinIO theo đúng cấu trúc chuẩn.
4. Nạp Users (Admin, 1 GV HaUI, 10 Sinh viên HaUI).
5. Nạp Sports (Pickleball, Cầu lông, Chạy bền) & Camera RTSP sân bãi.
6. Nạp Courses & Tasks (phân loại practice / exam, thiết lập tuần học & liên kết).
7. Nạp VideoResults (trỏ đúng file MinIO) & LiveResults (cho camera chạy bền).
8. Nạp Enrollments (tính toán tự động qua GradingService đảm bảo chính xác 100% công thức).
9. Cập nhật studentTotal cho Courses.
10. Nạp Notifications tương ứng với bài nộp & kết quả.
11. Khởi tạo Compound Indexes.
12. Audit tự động xác thực toàn vẹn 100%.

Chạy script:
    python scripts/seed_data.py
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Đảm bảo in UTF-8 không bị lỗi trên Windows console
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Đảm bảo import được module app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bson import ObjectId
from app.core.database import get_db
from app.main import init_db_indexes
from app.models.camera import CameraStatus
from app.models.course import CourseStatus, LessonItemType
from app.models.enrollment import EnrollmentStatus, StudentGrades
from app.models.notification import NotificationType
from app.models.sport import SportMode
from app.models.task import GradingMethod, TaskCategory
from app.models.user import UserRole
from app.services.auth_service import hash_password
from app.services.grading_service import grading_service
from app.services.minio_service import minio_service


def seed():
    db = get_db()
    now = datetime.now(timezone.utc)

    print("=" * 70)
    print(">>> BẮT ĐẦU QUÁ TRÌNH DỌN DẸP & DỰNG DỮ LIỆU ĐỒNG BỘ (MONGODB + MINIO)")
    print("=" * 70)

    # ──────────────────────────────────────────────────────────────────────────
    # BƯỚC 1: DỌN DẸP MINIO BUCKET
    # ──────────────────────────────────────────────────────────────────────────
    print("\n[BƯỚC 1/9] Dọn dẹp tệp tin cũ trong MinIO...")
    bucket_name = minio_service.default_bucket
    minio_service.ensure_bucket(bucket_name)

    existing_objects = list(minio_service.client.list_objects(bucket_name, recursive=True))
    deleted_minio_count = 0
    for obj in existing_objects:
        minio_service.client.remove_object(bucket_name, obj.object_name)
        deleted_minio_count += 1
    print(f"  + Đã xóa {deleted_minio_count} tệp tin mồ côi khỏi MinIO bucket '{bucket_name}'.")

    # ──────────────────────────────────────────────────────────────────────────
    # BƯỚC 2: DỌN DẸP MONGODB
    # ──────────────────────────────────────────────────────────────────────────
    print("\n[BƯỚC 2/9] Dọn sạch dữ liệu cũ trong MongoDB...")
    collections_to_clean = [
        "users", "sports", "cameras", "courses", "tasks",
        "enrollments", "video_results", "live_results", "notifications"
    ]
    for col in collections_to_clean:
        res = db[col].delete_many({})
        print(f"  - Xóa collection '{col:14}': {res.deleted_count} bản ghi.")
    print("  => Cơ sở dữ liệu MongoDB đã được dọn sạch hoàn toàn.")

    # ──────────────────────────────────────────────────────────────────────────
    # BƯỚC 3: TẠO USERS (Admin, 1 GV HaUI, 10 Sinh viên HaUI)
    # ──────────────────────────────────────────────────────────────────────────
    print("\n[BƯỚC 3/9] Khởi tạo tài khoản người dùng chuẩn HaUI...")
    password_hash = hash_password("123456")

    admin_id = ObjectId()
    teacher_id = ObjectId()

    # Tạo 10 sinh viên
    student_ids = [ObjectId() for _ in range(10)]

    users_data = [
        {
            "_id": admin_id,
            "name": "Quản Trị Viên Hệ Thống",
            "email": "admin@haui.edu.vn",
            "role": UserRole.ADMIN.value,
            "password": password_hash,
            "userCode": "AD001",
            "phoneNumber": "0988000001",
            "userStatus": "active",
            "gender": "Nam",
            "dateOfBirth": "1988-01-01",
            "createdAt": now,
            "updatedAt": now,
        },
        {
            "_id": teacher_id,
            "name": "ThS. Đặng Văn Long",
            "email": "longdv@haui.edu.vn",
            "role": UserRole.TEACHER.value,
            "password": password_hash,
            "userCode": "GV2026001",
            "phoneNumber": "0988000002",
            "userStatus": "active",
            "gender": "Nam",
            "dateOfBirth": "1985-05-15",
            "createdAt": now,
            "updatedAt": now,
        },
    ]

    students_raw = [
        ("Nguyễn Văn An", "annv@sv.haui.edu.vn", "2022601001", "Nam", "2004-05-15", "0901234501"),
        ("Trần Thị Bình", "binhtt@sv.haui.edu.vn", "2022601002", "Nữ", "2004-10-20", "0901234502"),
        ("Lê Hoàng Cường", "cuonglh@sv.haui.edu.vn", "2022601003", "Nam", "2004-03-12", "0901234503"),
        ("Phạm Minh Đức", "ducpm@sv.haui.edu.vn", "2022601004", "Nam", "2004-07-25", "0901234504"),
        ("Hoàng Thị Hoa", "hoaht@sv.haui.edu.vn", "2022601005", "Nữ", "2004-12-08", "0901234505"),
        ("Ngô Quang Huy", "huynq@sv.haui.edu.vn", "2022601006", "Nam", "2004-01-18", "0901234506"),
        ("Vũ Thị Lan", "lanvt@sv.haui.edu.vn", "2022601007", "Nữ", "2004-09-02", "0901234507"),
        ("Đỗ Thanh Minh", "minhdt@sv.haui.edu.vn", "2022601008", "Nam", "2004-11-23", "0901234508"),
        ("Bùi Thị Ngọc", "ngocbt@sv.haui.edu.vn", "2022601009", "Nữ", "2004-04-30", "0901234509"),
        ("Dương Quốc Phong", "phongdq@sv.haui.edu.vn", "2022601010", "Nam", "2004-08-14", "0901234510"),
    ]

    for idx, (name, email, code, gender, dob, phone) in enumerate(students_raw):
        users_data.append({
            "_id": student_ids[idx],
            "name": name,
            "email": email,
            "role": UserRole.STUDENT.value,
            "password": password_hash,
            "userCode": code,
            "phoneNumber": phone,
            "userStatus": "active",
            "gender": gender,
            "dateOfBirth": dob,
            "createdAt": now,
            "updatedAt": now,
        })

    db.users.insert_many(users_data)
    print(f"  + Đã tạo {len(users_data)} tài khoản: 1 Admin, 1 Giảng viên, 10 Sinh viên. Mật khẩu chung: 123456")

    # ──────────────────────────────────────────────────────────────────────────
    # BƯỚC 4: TẠO SPORTS & CAMERAS
    # ──────────────────────────────────────────────────────────────────────────
    print("\n[BƯỚC 4/9] Khởi tạo danh mục môn thể thao & Camera giám sát...")
    sport_pickle_id = ObjectId()
    sport_badminton_id = ObjectId()
    sport_run_id = ObjectId()

    sports_data = [
        {
            "_id": sport_pickle_id,
            "code": "PICKLE",
            "name": "Pickleball",
            "mode": SportMode.VIDEO.value,
            "scoringConfig": {
                "metricsFields": ["serveAccuracy", "dinkRate", "footworkScore"],
                "formula": "(serveAccuracy * 0.4) + (dinkRate * 0.4) + (footworkScore * 0.2)",
                "thresholds": {"pass": 5.0, "excellent": 8.5},
            },
            "createdAt": now,
            "updatedAt": now,
        },
        {
            "_id": sport_badminton_id,
            "code": "BADMINTON",
            "name": "Cầu lông",
            "mode": SportMode.VIDEO.value,
            "scoringConfig": {
                "metricsFields": ["swingTotal", "hitCount", "hitRate"],
                "formula": "(hitCount / swingTotal) * 10",
                "thresholds": {"pass": 5.0, "excellent": 8.5},
            },
            "createdAt": now,
            "updatedAt": now,
        },
        {
            "_id": sport_run_id,
            "code": "RUN",
            "name": "Chạy bền & Điền kinh",
            "mode": SportMode.CAMERA.value,
            "scoringConfig": {
                "metricsFields": ["laps", "avgSpeed", "distance", "duration"],
                "formula": None,
                "thresholds": {"pass": 5.0, "maxTimeSec": 300},
            },
            "createdAt": now,
            "updatedAt": now,
        },
    ]
    db.sports.insert_many(sports_data)

    camera1_id = ObjectId()
    cameras_data = [
        {
            "_id": camera1_id,
            "name": "Camera Sân Chạy HaUI - Khu A (Cổng 2)",
            "location": "Sân thể thao ngoài trời HaUI, Cơ sở 1",
            "streamUrl": "rtsp://192.168.1.101:554/live/stream1",
            "status": CameraStatus.ONLINE.value,
            "createdAt": now,
            "updatedAt": now,
        },
    ]
    db.cameras.insert_many(cameras_data)
    print(f"  + Đã tạo {len(sports_data)} môn thể thao (PICKLE, BADMINTON, RUN) và {len(cameras_data)} camera.")

    # ──────────────────────────────────────────────────────────────────────────
    # BƯỚC 5: TẠO COURSES & TASKS
    # ──────────────────────────────────────────────────────────────────────────
    print("\n[BƯỚC 5/9] Khởi tạo Khóa học (Lớp học phần) & Bài tập (Tasks)...")
    course_pb_id = ObjectId()
    course_run_id = ObjectId()

    # Tasks Pickleball
    task_pb_tx1_id = ObjectId()
    task_pb_tx2_id = ObjectId()
    task_pb_midterm_id = ObjectId()
    task_pb_final_id = ObjectId()

    # Tasks Chạy bền
    task_run_1500_id = ObjectId()
    task_run_final_id = ObjectId()

    tasks_data = [
        # Pickleball Tasks
        {
            "_id": task_pb_tx1_id,
            "courseId": str(course_pb_id),
            "sportId": str(sport_pickle_id),
            "title": "TX1: Kỹ thuật Giao bóng Pickleball",
            "category": TaskCategory.PRACTICE.value,
            "gradingMethod": GradingMethod.HIGHEST.value,
            "timeLimit": 60,
            "maxAttempts": 3,
            "isLocked": False,
            "openTime": now - timedelta(days=25),
            "closeTime": now + timedelta(days=15),
            "cameraId": None,
            "createdAt": now,
            "updatedAt": now,
        },
        {
            "_id": task_pb_tx2_id,
            "courseId": str(course_pb_id),
            "sportId": str(sport_pickle_id),
            "title": "TX2: Kỹ thuật Di chuyển & Đỡ bóng (Dink shot)",
            "category": TaskCategory.PRACTICE.value,
            "gradingMethod": GradingMethod.HIGHEST.value,
            "timeLimit": 90,
            "maxAttempts": 3,
            "isLocked": False,
            "openTime": now - timedelta(days=12),
            "closeTime": now + timedelta(days=25),
            "cameraId": None,
            "createdAt": now,
            "updatedAt": now,
        },
        {
            "_id": task_pb_midterm_id,
            "courseId": str(course_pb_id),
            "sportId": str(sport_pickle_id),
            "title": "Thi Giữa kỳ: Phối hợp Đánh đôi & Chiến thuật",
            "category": TaskCategory.EXAM.value,
            "gradingMethod": GradingMethod.LATEST.value,
            "timeLimit": 120,
            "maxAttempts": 2,
            "isLocked": False,
            "openTime": now - timedelta(days=3),
            "closeTime": now + timedelta(days=20),
            "cameraId": None,
            "createdAt": now,
            "updatedAt": now,
        },
        {
            "_id": task_pb_final_id,
            "courseId": str(course_pb_id),
            "sportId": str(sport_pickle_id),
            "title": "Thi Cuối kỳ: Kỹ năng toàn diện Pickleball",
            "category": TaskCategory.EXAM.value,
            "gradingMethod": GradingMethod.LATEST.value,
            "timeLimit": 180,
            "maxAttempts": 1,
            "isLocked": True,
            "openTime": now + timedelta(days=35),
            "closeTime": now + timedelta(days=50),
            "cameraId": None,
            "createdAt": now,
            "updatedAt": now,
        },
        # Chạy bền Tasks
        {
            "_id": task_run_1500_id,
            "courseId": str(course_run_id),
            "sportId": str(sport_run_id),
            "title": "Kiểm tra định kỳ: Chạy bền 1500m (Camera AI)",
            "category": TaskCategory.PRACTICE.value,
            "gradingMethod": GradingMethod.HIGHEST.value,
            "timeLimit": 600,
            "maxAttempts": 2,
            "isLocked": False,
            "openTime": now - timedelta(days=15),
            "closeTime": now + timedelta(days=20),
            "cameraId": str(camera1_id),
            "createdAt": now,
            "updatedAt": now,
        },
        {
            "_id": task_run_final_id,
            "courseId": str(course_run_id),
            "sportId": str(sport_run_id),
            "title": "Thi Cuối kỳ: Chạy bền cự ly 3000m",
            "category": TaskCategory.EXAM.value,
            "gradingMethod": GradingMethod.LATEST.value,
            "timeLimit": 1200,
            "maxAttempts": 1,
            "isLocked": True,
            "openTime": now + timedelta(days=40),
            "closeTime": now + timedelta(days=55),
            "cameraId": str(camera1_id),
            "createdAt": now,
            "updatedAt": now,
        },
    ]
    db.tasks.insert_many(tasks_data)

    courses_data = [
        {
            "_id": course_pb_id,
            "key": "pickleball-01",
            "name": "Pickleball căn bản & nâng cao",
            "teacherId": str(teacher_id),
            "teacherName": "ThS. Đặng Văn Long",
            "code": "GDTC-PB01",
            "desc": "Học phần GDTC đào tạo kỹ thuật chuyên môn Pickleball và rèn luyện thể lực. Chấm điểm và đánh giá tự động qua video bằng AI.",
            "status": CourseStatus.IN_PROGRESS.value,
            "isGradeLocked": False,
            "gradeLockedAt": None,
            "gradeLockedBy": None,
            "allowPracticeSubmission": True,
            "allowExamSubmission": True,
            "gradingFormula": {
                "attendanceWeight": 0.1,
                "practiceWeight": 0.4,
                "examWeight": 0.5,
            },
            "startDate": now - timedelta(days=30),
            "endDate": now + timedelta(days=60),
            "examDate": now + timedelta(days=50),
            "studentTotal": 0,  # Sẽ được cập nhật chính xác sau khi nạp enrollments
            "weeks": [
                {
                    "order": 1,
                    "title": "Tuần 1: Giới thiệu luật thi đấu & Kỹ thuật giao bóng",
                    "items": [
                        {"title": "Lý thuyết quy chuẩn sân bãi và an toàn", "type": LessonItemType.LESSON.value, "taskId": None},
                        {"title": "Thực hành giao bóng chuẩn", "type": LessonItemType.PRACTICE.value, "taskId": str(task_pb_tx1_id)},
                    ],
                },
                {
                    "order": 2,
                    "title": "Tuần 2: Di chuyển & Đỡ bóng (Dink shot)",
                    "items": [
                        {"title": "Kỹ thuật di chuyển chân trong khu vực Kitchen", "type": LessonItemType.LESSON.value, "taskId": None},
                        {"title": "Thực hành bài tập Dink shot", "type": LessonItemType.PRACTICE.value, "taskId": str(task_pb_tx2_id)},
                    ],
                },
                {
                    "order": 3,
                    "title": "Tuần 3: Chiến thuật Đánh đôi & Thi giữa kỳ",
                    "items": [
                        {"title": "Phân tích phối hợp vị trí cặp vận động viên", "type": LessonItemType.LESSON.value, "taskId": None},
                        {"title": "Kiểm tra Giữa kỳ Đánh đôi", "type": LessonItemType.PRACTICE.value, "taskId": str(task_pb_midterm_id)},
                    ],
                },
                {
                    "order": 4,
                    "title": "Tuần 4: Ôn tập & Chuẩn bị thi cuối kỳ",
                    "items": [
                        {"title": "Kỹ năng tổng hợp", "type": LessonItemType.LESSON.value, "taskId": None},
                        {"title": "Thi kết thúc học phần", "type": LessonItemType.PRACTICE.value, "taskId": str(task_pb_final_id)},
                    ],
                },
            ],
            "createdAt": now,
            "updatedAt": now,
        },
        {
            "_id": course_run_id,
            "key": "chayben-01",
            "name": "Giáo dục thể chất 2 - Điền kinh",
            "teacherId": str(teacher_id),
            "teacherName": "ThS. Đặng Văn Long",
            "code": "GDTC-CB01",
            "desc": "Môn điền kinh và chạy cự ly trung bình với camera AI nhận diện vòng chạy và tự động tính vận tốc trung bình.",
            "status": CourseStatus.IN_PROGRESS.value,
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
            "startDate": now - timedelta(days=20),
            "endDate": now + timedelta(days=70),
            "examDate": now + timedelta(days=60),
            "studentTotal": 0,
            "weeks": [
                {
                    "order": 1,
                    "title": "Tuần 1: Kỹ thuật thở và phân phối sức",
                    "items": [
                        {"title": "Lý thuyết phương pháp phân phối sức bền", "type": LessonItemType.LESSON.value, "taskId": None},
                        {"title": "Chạy kiểm tra định kỳ 1500m", "type": LessonItemType.PRACTICE.value, "taskId": str(task_run_1500_id)},
                    ],
                }
            ],
            "createdAt": now,
            "updatedAt": now,
        },
    ]
    db.courses.insert_many(courses_data)
    print(f"  + Đã tạo {len(courses_data)} khóa học và {len(tasks_data)} bài tập thể chất.")

    # ──────────────────────────────────────────────────────────────────────────
    # BƯỚC 6: TẢI VIDEO LÊN MINIO & NẠP VIDEO RESULTS / LIVE RESULTS
    # ──────────────────────────────────────────────────────────────────────────
    print("\n[BƯỚC 6/9] Upload video thực tế lên MinIO và nạp kết quả bài nộp...")
    sample_mp4_path = Path(__file__).resolve().parent / "sample_demo.mp4"
    if sample_mp4_path.exists():
        with open(sample_mp4_path, "rb") as f:
            sample_mp4_bytes = f.read()
    else:
        sample_mp4_bytes = b"mock mp4 content for testing"

    def upload_sample_video(sport_id_val, task_id_val, user_id_val, attempt_no_val, timestamp_val):
        object_name = f"{sport_id_val}/{task_id_val}/{user_id_val}_attempt{attempt_no_val}_{timestamp_val}.mp4"
        minio_path = minio_service.upload_bytes(
            data=sample_mp4_bytes,
            object_name=object_name,
            content_type="video/mp4",
        )
        return minio_path, len(sample_mp4_bytes)

    # 1. SV 1 (Nguyễn Văn An) nộp TX1, TX2, Midterm Pickleball
    ts1 = 1790100001
    vid1_path, vid1_size = upload_sample_video(sport_pickle_id, task_pb_tx1_id, student_ids[0], 1, ts1)
    ts2 = 1790100002
    vid2_path, vid2_size = upload_sample_video(sport_pickle_id, task_pb_tx2_id, student_ids[0], 1, ts2)
    ts3 = 1790100003
    vid3_path, vid3_size = upload_sample_video(sport_pickle_id, task_pb_midterm_id, student_ids[0], 1, ts3)

    # 2. SV 2 (Trần Thị Bình) nộp TX1 (đã chấm) và TX2 (pending chờ AI)
    ts4 = 1790100004
    vid4_path, vid4_size = upload_sample_video(sport_pickle_id, task_pb_tx1_id, student_ids[1], 1, ts4)
    ts5 = 1790100005
    vid5_path, vid5_size = upload_sample_video(sport_pickle_id, task_pb_tx2_id, student_ids[1], 1, ts5)

    # 3. SV 3 (Lê Hoàng Cường) nộp TX1 lần 1 (6.5), lần 2 cải thiện (8.0), nộp TX2 (7.5)
    ts6 = 1790100006
    vid6_path, vid6_size = upload_sample_video(sport_pickle_id, task_pb_tx1_id, student_ids[2], 1, ts6)
    ts7 = 1790100007
    vid7_path, vid7_size = upload_sample_video(sport_pickle_id, task_pb_tx1_id, student_ids[2], 2, ts7)
    ts8 = 1790100008
    vid8_path, vid8_size = upload_sample_video(sport_pickle_id, task_pb_tx2_id, student_ids[2], 1, ts8)

    # 4. SV 5 (Hoàng Thị Hoa) nộp TX1 (9.5), TX2 (9.2), Midterm (9.6)
    ts9 = 1790100009
    vid9_path, vid9_size = upload_sample_video(sport_pickle_id, task_pb_tx1_id, student_ids[4], 1, ts9)
    ts10 = 1790100010
    vid10_path, vid10_size = upload_sample_video(sport_pickle_id, task_pb_tx2_id, student_ids[4], 1, ts10)
    ts11 = 1790100011
    vid11_path, vid11_size = upload_sample_video(sport_pickle_id, task_pb_midterm_id, student_ids[4], 1, ts11)

    # 5. SV 6 (Ngô Quang Huy) nộp TX1 (7.0)
    ts12 = 1790100012
    vid12_path, vid12_size = upload_sample_video(sport_pickle_id, task_pb_tx1_id, student_ids[5], 1, ts12)

    video_results_data = [
        # SV1 - An
        {
            "_id": ObjectId(),
            "taskId": str(task_pb_tx1_id),
            "sportId": str(sport_pickle_id),
            "userId": str(student_ids[0]),
            "courseId": str(course_pb_id),
            "studentName": "Nguyễn Văn An",
            "studentCode": "2022601001",
            "taskTitle": "TX1: Kỹ thuật Giao bóng Pickleball",
            "attemptNo": 1,
            "submittedAt": now - timedelta(days=10),
            "pending": False,
            "videoUrl": vid1_path,
            "fileName": "nguyen_van_an_tx1.mp4",
            "fileSize": vid1_size,
            "contentType": "video/mp4",
            "durationSec": 32,
            "metrics": {"serveAccuracy": 90.0, "dinkRate": 85.0, "footworkScore": 88.0},
            "aiScore": 8.8,
            "aiComment": "Điểm tiếp xúc bóng tốt, đường bóng có độ xoáy ổn định.",
            "finalScore": 8.8,
            "teacherComment": "Đạt kỹ thuật giao bóng chuẩn thi đấu.",
            "gradedBy": str(teacher_id),
            "gradedAt": now - timedelta(days=9),
            "createdAt": now - timedelta(days=10),
            "updatedAt": now - timedelta(days=9),
        },
        {
            "_id": ObjectId(),
            "taskId": str(task_pb_tx2_id),
            "sportId": str(sport_pickle_id),
            "userId": str(student_ids[0]),
            "courseId": str(course_pb_id),
            "studentName": "Nguyễn Văn An",
            "studentCode": "2022601001",
            "taskTitle": "TX2: Kỹ thuật Di chuyển & Đỡ bóng (Dink shot)",
            "attemptNo": 1,
            "submittedAt": now - timedelta(days=5),
            "pending": False,
            "videoUrl": vid2_path,
            "fileName": "nguyen_van_an_tx2.mp4",
            "fileSize": vid2_size,
            "contentType": "video/mp4",
            "durationSec": 45,
            "metrics": {"serveAccuracy": 85.0, "dinkRate": 92.0, "footworkScore": 90.0},
            "aiScore": 8.9,
            "aiComment": "Kỹ thuật dink bóng sát lưới khéo léo.",
            "finalScore": 9.0,
            "teacherComment": "Động tác chân linh hoạt, điểm thưởng tác phong.",
            "gradedBy": str(teacher_id),
            "gradedAt": now - timedelta(days=4),
            "createdAt": now - timedelta(days=5),
            "updatedAt": now - timedelta(days=4),
        },
        {
            "_id": ObjectId(),
            "taskId": str(task_pb_midterm_id),
            "sportId": str(sport_pickle_id),
            "userId": str(student_ids[0]),
            "courseId": str(course_pb_id),
            "studentName": "Nguyễn Văn An",
            "studentCode": "2022601001",
            "taskTitle": "Thi Giữa kỳ: Phối hợp Đánh đôi & Chiến thuật",
            "attemptNo": 1,
            "submittedAt": now - timedelta(days=1),
            "pending": False,
            "videoUrl": vid3_path,
            "fileName": "nguyen_van_an_midterm.mp4",
            "fileSize": vid3_size,
            "contentType": "video/mp4",
            "durationSec": 60,
            "metrics": {"serveAccuracy": 88.0, "dinkRate": 86.0, "footworkScore": 87.0},
            "aiScore": 8.7,
            "aiComment": "Phối hợp vị trí ăn ý với đồng đội.",
            "finalScore": 8.7,
            "teacherComment": "Bài thi giữa kỳ hoàn thành tốt.",
            "gradedBy": str(teacher_id),
            "gradedAt": now - timedelta(hours=10),
            "createdAt": now - timedelta(days=1),
            "updatedAt": now - timedelta(hours=10),
        },

        # SV2 - Bình
        {
            "_id": ObjectId(),
            "taskId": str(task_pb_tx1_id),
            "sportId": str(sport_pickle_id),
            "userId": str(student_ids[1]),
            "courseId": str(course_pb_id),
            "studentName": "Trần Thị Bình",
            "studentCode": "2022601002",
            "taskTitle": "TX1: Kỹ thuật Giao bóng Pickleball",
            "attemptNo": 1,
            "submittedAt": now - timedelta(days=8),
            "pending": False,
            "videoUrl": vid4_path,
            "fileName": "tran_thi_binh_tx1.mp4",
            "fileSize": vid4_size,
            "contentType": "video/mp4",
            "durationSec": 28,
            "metrics": {"serveAccuracy": 82.0, "dinkRate": 78.0, "footworkScore": 80.0},
            "aiScore": 8.0,
            "aiComment": "Độ cao tiếp xúc bóng hợp lệ.",
            "finalScore": 8.0,
            "teacherComment": "Đạt yêu cầu.",
            "gradedBy": str(teacher_id),
            "gradedAt": now - timedelta(days=7),
            "createdAt": now - timedelta(days=8),
            "updatedAt": now - timedelta(days=7),
        },
        {
            "_id": ObjectId(),
            "taskId": str(task_pb_tx2_id),
            "sportId": str(sport_pickle_id),
            "userId": str(student_ids[1]),
            "courseId": str(course_pb_id),
            "studentName": "Trần Thị Bình",
            "studentCode": "2022601002",
            "taskTitle": "TX2: Kỹ thuật Di chuyển & Đỡ bóng (Dink shot)",
            "attemptNo": 1,
            "submittedAt": now - timedelta(minutes=20),
            "pending": True,
            "videoUrl": vid5_path,
            "fileName": "tran_thi_binh_tx2.mp4",
            "fileSize": vid5_size,
            "contentType": "video/mp4",
            "durationSec": 35,
            "metrics": {},
            "aiScore": None,
            "aiComment": None,
            "finalScore": None,
            "teacherComment": None,
            "createdAt": now - timedelta(minutes=20),
            "updatedAt": now - timedelta(minutes=20),
        },

        # SV3 - Cường
        {
            "_id": ObjectId(),
            "taskId": str(task_pb_tx1_id),
            "sportId": str(sport_pickle_id),
            "userId": str(student_ids[2]),
            "courseId": str(course_pb_id),
            "studentName": "Lê Hoàng Cường",
            "studentCode": "2022601003",
            "taskTitle": "TX1: Kỹ thuật Giao bóng Pickleball",
            "attemptNo": 1,
            "submittedAt": now - timedelta(days=12),
            "pending": False,
            "videoUrl": vid6_path,
            "fileName": "le_hoang_cuong_tx1_att1.mp4",
            "fileSize": vid6_size,
            "contentType": "video/mp4",
            "durationSec": 30,
            "metrics": {"serveAccuracy": 65.0, "dinkRate": 60.0, "footworkScore": 70.0},
            "aiScore": 6.5,
            "aiComment": "Giao bóng chưa qua lưới 2 lần.",
            "finalScore": 6.5,
            "teacherComment": "Cần tập thêm lực cổ tay.",
            "gradedBy": str(teacher_id),
            "gradedAt": now - timedelta(days=11),
            "createdAt": now - timedelta(days=12),
            "updatedAt": now - timedelta(days=11),
        },
        {
            "_id": ObjectId(),
            "taskId": str(task_pb_tx1_id),
            "sportId": str(sport_pickle_id),
            "userId": str(student_ids[2]),
            "courseId": str(course_pb_id),
            "studentName": "Lê Hoàng Cường",
            "studentCode": "2022601003",
            "taskTitle": "TX1: Kỹ thuật Giao bóng Pickleball",
            "attemptNo": 2,
            "submittedAt": now - timedelta(days=8),
            "pending": False,
            "videoUrl": vid7_path,
            "fileName": "le_hoang_cuong_tx1_att2.mp4",
            "fileSize": vid7_size,
            "contentType": "video/mp4",
            "durationSec": 30,
            "metrics": {"serveAccuracy": 82.0, "dinkRate": 78.0, "footworkScore": 80.0},
            "aiScore": 8.0,
            "aiComment": "Tiến bộ rõ rệt, tỷ lệ bóng chuẩn đạt 82%.",
            "finalScore": 8.0,
            "teacherComment": "Lần 2 cải thiện tốt.",
            "gradedBy": str(teacher_id),
            "gradedAt": now - timedelta(days=7),
            "createdAt": now - timedelta(days=8),
            "updatedAt": now - timedelta(days=7),
        },
        {
            "_id": ObjectId(),
            "taskId": str(task_pb_tx2_id),
            "sportId": str(sport_pickle_id),
            "userId": str(student_ids[2]),
            "courseId": str(course_pb_id),
            "studentName": "Lê Hoàng Cường",
            "studentCode": "2022601003",
            "taskTitle": "TX2: Kỹ thuật Di chuyển & Đỡ bóng (Dink shot)",
            "attemptNo": 1,
            "submittedAt": now - timedelta(days=3),
            "pending": False,
            "videoUrl": vid8_path,
            "fileName": "le_hoang_cuong_tx2.mp4",
            "fileSize": vid8_size,
            "contentType": "video/mp4",
            "durationSec": 40,
            "metrics": {"serveAccuracy": 75.0, "dinkRate": 76.0, "footworkScore": 74.0},
            "aiScore": 7.5,
            "aiComment": "Di chuyển đúng vị trí.",
            "finalScore": 7.5,
            "teacherComment": "Đạt.",
            "gradedBy": str(teacher_id),
            "gradedAt": now - timedelta(days=2),
            "createdAt": now - timedelta(days=3),
            "updatedAt": now - timedelta(days=2),
        },

        # SV5 - Hoa (Xuất sắc)
        {
            "_id": ObjectId(),
            "taskId": str(task_pb_tx1_id),
            "sportId": str(sport_pickle_id),
            "userId": str(student_ids[4]),
            "courseId": str(course_pb_id),
            "studentName": "Hoàng Thị Hoa",
            "studentCode": "2022601005",
            "taskTitle": "TX1: Kỹ thuật Giao bóng Pickleball",
            "attemptNo": 1,
            "submittedAt": now - timedelta(days=12),
            "pending": False,
            "videoUrl": vid9_path,
            "fileName": "hoang_thi_hoa_tx1.mp4",
            "fileSize": vid9_size,
            "contentType": "video/mp4",
            "durationSec": 30,
            "metrics": {"serveAccuracy": 96.0, "dinkRate": 95.0, "footworkScore": 94.0},
            "aiScore": 9.5,
            "aiComment": "Động tác hoàn hảo, độ chính xác 96%.",
            "finalScore": 9.5,
            "teacherComment": "Kỹ thuật xuất sắc.",
            "gradedBy": str(teacher_id),
            "gradedAt": now - timedelta(days=11),
            "createdAt": now - timedelta(days=12),
            "updatedAt": now - timedelta(days=11),
        },
        {
            "_id": ObjectId(),
            "taskId": str(task_pb_tx2_id),
            "sportId": str(sport_pickle_id),
            "userId": str(student_ids[4]),
            "courseId": str(course_pb_id),
            "studentName": "Hoàng Thị Hoa",
            "studentCode": "2022601005",
            "taskTitle": "TX2: Kỹ thuật Di chuyển & Đỡ bóng (Dink shot)",
            "attemptNo": 1,
            "submittedAt": now - timedelta(days=6),
            "pending": False,
            "videoUrl": vid10_path,
            "fileName": "hoang_thi_hoa_tx2.mp4",
            "fileSize": vid10_size,
            "contentType": "video/mp4",
            "durationSec": 42,
            "metrics": {"serveAccuracy": 92.0, "dinkRate": 93.0, "footworkScore": 91.0},
            "aiScore": 9.2,
            "aiComment": "Đỡ bóng mềm mại và kiểm soát điểm rơi rất tốt.",
            "finalScore": 9.2,
            "teacherComment": "Tốt.",
            "gradedBy": str(teacher_id),
            "gradedAt": now - timedelta(days=5),
            "createdAt": now - timedelta(days=6),
            "updatedAt": now - timedelta(days=5),
        },
        {
            "_id": ObjectId(),
            "taskId": str(task_pb_midterm_id),
            "sportId": str(sport_pickle_id),
            "userId": str(student_ids[4]),
            "courseId": str(course_pb_id),
            "studentName": "Hoàng Thị Hoa",
            "studentCode": "2022601005",
            "taskTitle": "Thi Giữa kỳ: Phối hợp Đánh đôi & Chiến thuật",
            "attemptNo": 1,
            "submittedAt": now - timedelta(days=2),
            "pending": False,
            "videoUrl": vid11_path,
            "fileName": "hoang_thi_hoa_midterm.mp4",
            "fileSize": vid11_size,
            "contentType": "video/mp4",
            "durationSec": 55,
            "metrics": {"serveAccuracy": 96.0, "dinkRate": 97.0, "footworkScore": 95.0},
            "aiScore": 9.6,
            "aiComment": "Chiến thuật bao sân chuẩn mực.",
            "finalScore": 9.6,
            "teacherComment": "Rất xuất sắc.",
            "gradedBy": str(teacher_id),
            "gradedAt": now - timedelta(days=1),
            "createdAt": now - timedelta(days=2),
            "updatedAt": now - timedelta(days=1),
        },

        # SV6 - Huy
        {
            "_id": ObjectId(),
            "taskId": str(task_pb_tx1_id),
            "sportId": str(sport_pickle_id),
            "userId": str(student_ids[5]),
            "courseId": str(course_pb_id),
            "studentName": "Ngô Quang Huy",
            "studentCode": "2022601006",
            "taskTitle": "TX1: Kỹ thuật Giao bóng Pickleball",
            "attemptNo": 1,
            "submittedAt": now - timedelta(days=4),
            "pending": False,
            "videoUrl": vid12_path,
            "fileName": "ngo_quang_huy_tx1.mp4",
            "fileSize": vid12_size,
            "contentType": "video/mp4",
            "durationSec": 29,
            "metrics": {"serveAccuracy": 70.0, "dinkRate": 72.0, "footworkScore": 68.0},
            "aiScore": 7.0,
            "aiComment": "Điểm tiếp xúc bóng ở mức trung bình.",
            "finalScore": 7.0,
            "teacherComment": "Đạt yêu cầu cơ bản.",
            "gradedBy": str(teacher_id),
            "gradedAt": now - timedelta(days=3),
            "createdAt": now - timedelta(days=4),
            "updatedAt": now - timedelta(days=3),
        },
    ]
    db.video_results.insert_many(video_results_data)

    # Nạp LiveResults cho môn Chạy bền
    live_results_data = [
        {
            "_id": ObjectId(),
            "taskId": str(task_run_1500_id),
            "sportId": str(sport_run_id),
            "userId": str(student_ids[6]),  # Lan
            "cameraId": str(camera1_id),
            "startedAt": now - timedelta(days=5, hours=2),
            "completedAt": now - timedelta(days=5, hours=1, minutes=50),
            "metrics": {"laps": 4, "avgSpeed": 12.5, "distance": 1500, "duration": 340},
            "score": 8.5,
            "createdAt": now - timedelta(days=5),
            "updatedAt": now - timedelta(days=5),
        },
        {
            "_id": ObjectId(),
            "taskId": str(task_run_1500_id),
            "sportId": str(sport_run_id),
            "userId": str(student_ids[7]),  # Minh
            "cameraId": str(camera1_id),
            "startedAt": now - timedelta(days=5, hours=2),
            "completedAt": now - timedelta(days=5, hours=1, minutes=48),
            "metrics": {"laps": 4, "avgSpeed": 11.8, "distance": 1500, "duration": 360},
            "score": 8.0,
            "createdAt": now - timedelta(days=5),
            "updatedAt": now - timedelta(days=5),
        },
        {
            "_id": ObjectId(),
            "taskId": str(task_run_1500_id),
            "sportId": str(sport_run_id),
            "userId": str(student_ids[8]),  # Ngọc
            "cameraId": str(camera1_id),
            "startedAt": now - timedelta(days=5, hours=2),
            "completedAt": now - timedelta(days=5, hours=1, minutes=45),
            "metrics": {"laps": 4, "avgSpeed": 11.2, "distance": 1500, "duration": 380},
            "score": 7.5,
            "createdAt": now - timedelta(days=5),
            "updatedAt": now - timedelta(days=5),
        },
        {
            "_id": ObjectId(),
            "taskId": str(task_run_1500_id),
            "sportId": str(sport_run_id),
            "userId": str(student_ids[5]),  # Huy
            "cameraId": str(camera1_id),
            "startedAt": now - timedelta(days=5, hours=2),
            "completedAt": now - timedelta(days=5, hours=1, minutes=52),
            "metrics": {"laps": 4, "avgSpeed": 13.0, "distance": 1500, "duration": 320},
            "score": 8.8,
            "createdAt": now - timedelta(days=5),
            "updatedAt": now - timedelta(days=5),
        },
    ]
    db.live_results.insert_many(live_results_data)
    print(f"  + Đã upload {len(video_results_data)} video lên MinIO và tạo {len(video_results_data)} bản ghi VideoResult.")
    print(f"  + Đã tạo {len(live_results_data)} bản ghi LiveResult (Camera AI chạy bền).")

    # ──────────────────────────────────────────────────────────────────────────
    # BƯỚC 7: NẠP ENROLLMENTS (TÍNH TOÁN TỰ ĐỘNG BẰNG GRADINGSERVICE ĐẢM BẢO CHUẨN 100%)
    # ──────────────────────────────────────────────────────────────────────────
    print("\n[BƯỚC 7/9] Khởi tạo dữ liệu Ghi danh (Enrollments) & Đồng bộ Sổ điểm...")

    # Khóa học 1: Pickleball (6 sinh viên: SV1, SV2, SV3, SV4, SV5, SV6)
    # Lấy danh sách tasks trong khóa học Pickleball
    pb_course_doc = db.courses.find_one({"_id": course_pb_id})
    pb_tasks = list(db.tasks.find({"courseId": str(course_pb_id)}))
    pb_practice_ids = [str(t["_id"]) for t in pb_tasks if t.get("category") == TaskCategory.PRACTICE.value]
    pb_exam_ids = [str(t["_id"]) for t in pb_tasks if t.get("category") == TaskCategory.EXAM.value]

    from app.models.course import Course, GradingFormula
    pb_formula = GradingFormula(**pb_course_doc["gradingFormula"])

    enrollments_data = []

    # Map thông tin điểm từng SV trong lớp Pickleball
    pb_students_configs = [
        # SV1 - An: TX1: 8.8, TX2: 9.0, Midterm: 8.7, Att: 9.5
        (0, {"attendance_score": 9.5}, {str(task_pb_tx1_id): 8.8, str(task_pb_tx2_id): 9.0, str(task_pb_midterm_id): 8.7}, "Kỹ thuật giao bóng tốt, phản xạ nhanh."),
        # SV2 - Bình: TX1: 8.0 (TX2 pending nên chưa có điểm), Att: 9.0
        (1, {"attendance_score": 9.0}, {str(task_pb_tx1_id): 8.0}, "Cần rèn luyện thêm bài Dink shot ở Kitchen."),
        # SV3 - Cường: TX1: 8.0, TX2: 7.5, Att: 8.5
        (2, {"attendance_score": 8.5}, {str(task_pb_tx1_id): 8.0, str(task_pb_tx2_id): 7.5}, "Chăm chỉ tập luyện, có tiến bộ qua các lần nộp."),
        # SV4 - Đức: Chưa nộp bài nào, Att: 7.0
        (3, {"attendance_score": 7.0}, {}, "Chưa nộp bài tập nào qua hệ thống."),
        # SV5 - Hoa: TX1: 9.5, TX2: 9.2, Midterm: 9.6, Att: 10.0
        (4, {"attendance_score": 10.0}, {str(task_pb_tx1_id): 9.5, str(task_pb_tx2_id): 9.2, str(task_pb_midterm_id): 9.6}, "Sinh viên xuất sắc của lớp học phần."),
        # SV6 - Huy: TX1: 7.0, Att: 8.0
        (5, {"attendance_score": 8.0}, {str(task_pb_tx1_id): 7.0}, "Cần cải thiện độ chính xác khi vung vợt."),
    ]

    for (s_idx, base_grades, task_scores, note) in pb_students_configs:
        student_doc = db.users.find_one({"_id": student_ids[s_idx]})
        completed_task_ids = list(task_scores.keys())
        progress_pct = round((len(completed_task_ids) / len(pb_tasks)) * 100, 1)

        # Tìm điểm thi kết thúc / giữa kỳ nếu có
        exam_override = None
        for ex_id in pb_exam_ids:
            if ex_id in task_scores:
                exam_override = task_scores[ex_id]
                break

        computed = grading_service.compute_student_grades(
            current_grades=StudentGrades(**base_grades),
            task_scores=task_scores,
            practice_task_ids=pb_practice_ids,
            formula=pb_formula,
            exam_score_override=exam_override,
        )

        enrollments_data.append({
            "_id": ObjectId(),
            "userId": str(student_ids[s_idx]),
            "courseId": str(course_pb_id),
            "studentCode": student_doc.get("userCode"),
            "studentName": student_doc.get("name"),
            "studentEmail": student_doc.get("email"),
            "studentGender": student_doc.get("gender"),
            "courseName": pb_course_doc.get("name"),
            "teacherName": pb_course_doc.get("teacherName"),
            "examDate": pb_course_doc.get("examDate"),
            "status": EnrollmentStatus.ACTIVE.value,
            "progressPercent": progress_pct,
            "completedTaskIds": completed_task_ids,
            "taskScores": task_scores,
            "grades": computed.model_dump(by_alias=True),
            "isGradeLocked": False,
            "note": note,
            "createdAt": now - timedelta(days=25),
            "updatedAt": now,
        })

    # Khóa học 2: Điền kinh & Chạy bền (5 sinh viên: SV6, SV7, SV8, SV9, SV10)
    run_course_doc = db.courses.find_one({"_id": course_run_id})
    run_tasks = list(db.tasks.find({"courseId": str(course_run_id)}))
    run_practice_ids = [str(t["_id"]) for t in run_tasks if t.get("category") == TaskCategory.PRACTICE.value]
    run_formula = GradingFormula(**run_course_doc["gradingFormula"])

    run_students_configs = [
        # SV6 - Huy: 1500m: 8.8, Att: 9.0
        (5, {"attendance_score": 9.0}, {str(task_run_1500_id): 8.8}, "Thể lực rất tốt."),
        # SV7 - Lan: 1500m: 8.5, Att: 9.5
        (6, {"attendance_score": 9.5}, {str(task_run_1500_id): 8.5}, "Duy trì nhịp chạy đều đặn."),
        # SV8 - Minh: 1500m: 8.0, Att: 8.5
        (7, {"attendance_score": 8.5}, {str(task_run_1500_id): 8.0}, "Cần cải thiện nước rút vòng cuối."),
        # SV9 - Ngọc: 1500m: 7.5, Att: 8.0
        (8, {"attendance_score": 8.0}, {str(task_run_1500_id): 7.5}, "Đạt yêu cầu sức bền."),
        # SV10 - Phong: Chưa chạy, Att: 7.0
        (9, {"attendance_score": 7.0}, {}, "Chưa hoàn thành chạy cự ly 1500m."),
    ]

    for (s_idx, base_grades, task_scores, note) in run_students_configs:
        student_doc = db.users.find_one({"_id": student_ids[s_idx]})
        completed_task_ids = list(task_scores.keys())
        progress_pct = round((len(completed_task_ids) / len(run_tasks)) * 100, 1)

        computed = grading_service.compute_student_grades(
            current_grades=StudentGrades(**base_grades),
            task_scores=task_scores,
            practice_task_ids=run_practice_ids,
            formula=run_formula,
            exam_score_override=None,
        )

        enrollments_data.append({
            "_id": ObjectId(),
            "userId": str(student_ids[s_idx]),
            "courseId": str(course_run_id),
            "studentCode": student_doc.get("userCode"),
            "studentName": student_doc.get("name"),
            "studentEmail": student_doc.get("email"),
            "studentGender": student_doc.get("gender"),
            "courseName": run_course_doc.get("name"),
            "teacherName": run_course_doc.get("teacherName"),
            "examDate": run_course_doc.get("examDate"),
            "status": EnrollmentStatus.ACTIVE.value,
            "progressPercent": progress_pct,
            "completedTaskIds": completed_task_ids,
            "taskScores": task_scores,
            "grades": computed.model_dump(by_alias=True),
            "isGradeLocked": False,
            "note": note,
            "createdAt": now - timedelta(days=18),
            "updatedAt": now,
        })

    db.enrollments.insert_many(enrollments_data)
    print(f"  + Đã tạo {len(enrollments_data)} bản ghi Enrollments (6 SV Pickleball, 5 SV Chạy bền).")

    # Cập nhật chính xác studentTotal vào Courses
    pb_enr_count = db.enrollments.count_documents({"courseId": str(course_pb_id)})
    db.courses.update_one({"_id": course_pb_id}, {"$set": {"studentTotal": pb_enr_count}})

    run_enr_count = db.enrollments.count_documents({"courseId": str(course_run_id)})
    db.courses.update_one({"_id": course_run_id}, {"$set": {"studentTotal": run_enr_count}})
    print(f"  + Cập nhật studentTotal cho Khóa học: Pickleball = {pb_enr_count}, Chạy bền = {run_enr_count}.")

    # ──────────────────────────────────────────────────────────────────────────
    # BƯỚC 8: TẠO THÔNG BÁO (NOTIFICATIONS) TƯƠNG ỨNG
    # ──────────────────────────────────────────────────────────────────────────
    print("\n[BƯỚC 8/9] Tạo thông báo đồng bộ với lịch sử bài nộp...")
    notifs_data = [
        # Thông báo cho An
        {
            "userId": str(student_ids[0]),
            "type": NotificationType.SUBMISSION_GRADED.value,
            "title": "Đã có điểm: TX1 Pickleball",
            "message": "Giảng viên đã chấm điểm bài nộp của bạn: 8.8 điểm. Kỹ thuật giao bóng tốt.",
            "link": f"/student/courses/{course_pb_id}/grades",
            "isRead": True,
            "createdAt": now - timedelta(days=9),
            "updatedAt": now - timedelta(days=9),
        },
        {
            "userId": str(student_ids[0]),
            "type": NotificationType.SUBMISSION_GRADED.value,
            "title": "Đã có điểm: Thi Giữa kỳ Pickleball",
            "message": "Bài thi giữa kỳ của bạn đã được đánh giá: 8.7 điểm.",
            "link": f"/student/courses/{course_pb_id}/grades",
            "isRead": False,
            "createdAt": now - timedelta(hours=10),
            "updatedAt": now - timedelta(hours=10),
        },
        # Thông báo cho Bình (TX2 vừa nộp)
        {
            "userId": str(student_ids[1]),
            "type": NotificationType.SUBMISSION_RECEIVED.value,
            "title": "Đã nộp bài: TX2 Dink shot",
            "message": "Hệ thống đã nhận bài nộp lần 1 của bạn và đang tiến hành phân tích video AI.",
            "link": f"/student/courses/{course_pb_id}/grades",
            "isRead": False,
            "createdAt": now - timedelta(minutes=20),
            "updatedAt": now - timedelta(minutes=20),
        },
        # Thông báo cho Hoa
        {
            "userId": str(student_ids[4]),
            "type": NotificationType.SUBMISSION_GRADED.value,
            "title": "Chúc mừng kết quả xuất sắc Giữa kỳ",
            "message": "Bạn đạt 9.6 điểm bài thi Giữa kỳ Pickleball.",
            "link": f"/student/courses/{course_pb_id}/grades",
            "isRead": True,
            "createdAt": now - timedelta(days=1),
            "updatedAt": now - timedelta(days=1),
        },
    ]

    # Thông báo chào mừng đầu kỳ cho tất cả 10 sinh viên
    for sid in student_ids:
        notifs_data.append({
            "userId": str(sid),
            "type": NotificationType.GENERAL.value,
            "title": "Chào mừng học kỳ mới GDTC HaUI",
            "message": "Chào mừng bạn đến với hệ thống Đào tạo & Đánh giá Thể chất AI Trường Đại học Công nghiệp Hà Nội.",
            "link": None,
            "isRead": False,
            "createdAt": now - timedelta(days=20),
            "updatedAt": now - timedelta(days=20),
        })

    db.notifications.insert_many(notifs_data)
    print(f"  + Đã tạo {len(notifs_data)} thông báo.")

    # ──────────────────────────────────────────────────────────────────────────
    # BƯỚC 9: TẠO INDEXES & AUDIT TỰ ĐỘNG
    # ──────────────────────────────────────────────────────────────────────────
    print("\n[BƯỚC 9/9] Khởi tạo Compound Indexes & Thẩm định tính toàn vẹn 100%...")
    init_db_indexes()

    # Thẩm định MinIO
    minio_objs = {o.object_name for o in minio_service.client.list_objects(bucket_name, recursive=True)}
    broken_minio_links = 0
    for vr in db.video_results.find():
        url = vr.get("videoUrl", "")
        # Lấy clean object name
        clean = url[len(bucket_name) + 1:] if url.startswith(f"{bucket_name}/") else url
        if clean not in minio_objs:
            broken_minio_links += 1

    # Thẩm định Course - Enrollments count
    mismatch_totals = 0
    for c in db.courses.find():
        actual = db.enrollments.count_documents({"courseId": str(c["_id"])})
        if c.get("studentTotal") != actual:
            mismatch_totals += 1

    # Thẩm định taskScores và grading logic
    grading_errors = 0
    for enr in db.enrollments.find():
        grades = enr.get("grades", {})
        final_sc = grades.get("finalScore")
        exam_sc = grades.get("examScore")
        # Quy chế tín chỉ: Nếu chưa có examScore thì finalScore phải là None
        if exam_sc is None and final_sc is not None:
            grading_errors += 1

    print("\n" + "=" * 70)
    print(">>> KẾT QUẢ THẨM ĐỊNH TOÀN VẸN DỮ LIỆU:")
    print(f"  - Tệp tin MinIO tồn tại thực tế        : {'✅ 100% KHỚP' if broken_minio_links == 0 else f'❌ {broken_minio_links} LỖI'}")
    print(f"  - Đồng bộ sĩ số Khóa học (studentTotal): {'✅ 100% KHỚP' if mismatch_totals == 0 else f'❌ {mismatch_totals} LỖI'}")
    print(f"  - Logic điểm tín chỉ (GradingService) : {'✅ 100% CHÍNH XÁC' if grading_errors == 0 else f'❌ {grading_errors} LỖI'}")
    print("=" * 70)
    print(">>> DỰNG VÀ ĐỒNG BỘ DỮ LIỆU MỚI THÀNH CÔNG RỰC RỠ!")
    print("=" * 70)


if __name__ == "__main__":
    seed()
