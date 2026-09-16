"""Versioned REST API matching api.md."""
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pymongo.errors import DuplicateKeyError

from app.core.config import settings
from app.core.database import clean, collection, now, object_id
from app.core.security import create_access_token, get_current_user, hash_password, require_roles, verify_password
from app.schemas.api import (
    CameraInput, CameraPatch, CourseInput, CoursePatch, EnrollmentInput, GradeLiveInput,
    GradeVideoInput, LiveInput, LivePatch, LoginRequest, SportInput, SportPatch, TaskInput,
    TaskPatch, UserInput,
)

router = APIRouter()
admin_or_teacher = require_roles("admin", "teacher")
admin_only = require_roles("admin")


def doc(name: str, identifier: str) -> dict[str, Any]:
    try:
        item = clean(collection(name).find_one({"_id": object_id(identifier)}))
    except ValueError:
        item = None
    if item is None:
        raise HTTPException(404, f"{name[:-1].capitalize()} not found")
    return item


def envelope(data: Any, message: str | None = None) -> dict[str, Any]:
    result = {"data": data}
    if message:
        result["message"] = message
    return result


def page_result(items: list[dict[str, Any]], page: int, page_size: int, total: int) -> dict[str, Any]:
    return {"data": items, "pagination": {"page": page, "pageSize": page_size, "total": total, "totalPages": (total + page_size - 1) // page_size}}


def list_docs(name: str, query: dict[str, Any], page: int, page_size: int) -> dict[str, Any]:
    total = collection(name).count_documents(query)
    cursor = collection(name).find(query).skip((page - 1) * page_size).limit(page_size)
    return page_result([clean(item) for item in cursor], page, page_size, total)


def public_user(user: dict[str, Any]) -> dict[str, Any]:
    user_id = str(user.get("_id", user.get("id")))
    code = user.get("studentCode") or user.get("userCode") or user.get("username", "")
    return {
        "id": user_id,
        "name": user.get("name", user.get("fullName", user.get("username", ""))),
        "email": user.get("email", ""),
        "role": user.get("role", "student"),
        "studentCode": code,
        "userCode": code,
        "phoneNumber": user.get("phoneNumber", user.get("phone", "")),
        "dateOfBirth": user.get("dateOfBirth", user.get("birthDate", "")),
        "userStatus": user.get("status", "active"),
        "status": user.get("status", "active"),
    }


def validate_task(mode: str, camera_id: str | None) -> None:
    if mode == "video" and camera_id is not None:
        raise HTTPException(422, "Video tasks must not reference a camera")
    if mode == "camera" and not camera_id:
        raise HTTPException(422, "Camera tasks require cameraId")
    if camera_id:
        doc("cameras", camera_id)


@router.post("/auth/login", tags=["Auth"])
def login(payload: LoginRequest):
    identifier = payload.username or payload.email
    if not identifier:
        raise HTTPException(422, "Username or email is required")
    user = collection("users").find_one({"$or": [{"username": identifier}, {"email": identifier}]})
    if not user or not verify_password(payload.password, user.get("passwordHash", user.get("password", ""))):
        raise HTTPException(401, "Invalid username or password")
    if user.get("status", "active") != "active":
        raise HTTPException(403, "User account is inactive")
    user_id = str(user["_id"])
    token = create_access_token({"sub": user_id})
    return envelope({"accessToken": token, "access_token": token, "tokenType": "bearer", "token_type": "bearer", "user": public_user(user)}, "Login successful")


@router.get("/auth/me", tags=["Auth"])
def me(user: dict = Depends(get_current_user)):
    return envelope(public_user(user))


@router.post("/auth/logout", tags=["Auth"])
def logout(_: dict = Depends(get_current_user)):
    return {"message": "Logout successful"}


@router.get("/users/{user_id}", tags=["Users"])
def get_user(user_id: str, _: dict = Depends(get_current_user)):
    user = doc("users", user_id)
    return envelope(public_user(user))


@router.post("/users", status_code=201, tags=["Users"])
def create_user(payload: UserInput, _: dict = Depends(admin_only)):
    user = {
        "username": payload.username,
        "passwordHash": hash_password(payload.password),
        "name": payload.name,
        "role": payload.role,
        "status": "active",
        "createdAt": now(),
        "updatedAt": now(),
    }
    if payload.email is not None:
        user["email"] = payload.email
    if payload.studentCode is not None:
        user["studentCode"] = payload.studentCode
    try:
        result = collection("users").insert_one(user)
    except DuplicateKeyError:
        raise HTTPException(409, "Username or email already exists")
    return envelope(public_user({**user, "_id": result.inserted_id}), "User created successfully")


@router.get("/dashboard/student", tags=["Dashboard"])
def student_dashboard(courseId: str | None = None, user: dict = Depends(get_current_user)):
    user_id = user["id"]
    query = {"userId": user_id}
    if courseId:
        query["courseId"] = courseId
    enrollments = [clean(x) for x in collection("enrollments").find(query)]
    course_ids = [x["courseId"] for x in enrollments]
    courses = [clean(x) for x in collection("courses").find({"_id": {"$in": [object_id(x) for x in course_ids if object_id(x)]}})] if course_ids else []
    results = [clean(x) for x in collection("video_results").find({"userId": user_id}).sort("submittedAt", -1).limit(5)]
    return envelope({"student": public_user(user), "courses": courses, "recentResults": results, "summary": {"courseCount": len(courses), "completedTaskCount": sum(len(x.get("completedTaskIds", [])) for x in enrollments), "averageScore": None}})


@router.get("/dashboard/teacher", tags=["Dashboard"])
def teacher_dashboard(courseId: str | None = None, _: dict = Depends(admin_or_teacher)):
    query = {"_id": object_id(courseId)} if courseId else {}
    courses = [clean(x) for x in collection("courses").find(query)]
    course_ids = [x["id"] for x in courses]
    student_count = collection("enrollments").count_documents({"courseId": {"$in": course_ids}}) if course_ids else 0
    pending = collection("video_results").count_documents({"pending": True})
    completed = collection("video_results").count_documents({"pending": False}) + collection("live_results").count_documents({"completedAt": {"$ne": None}})
    return envelope({"summary": {"courseCount": len(courses), "studentCount": student_count, "pendingVideoResults": pending, "completedAssessments": completed}, "courses": courses})


@router.get("/sports", tags=["Sports"])
def list_sports(page: int = Query(1, ge=1), pageSize: int = Query(20, ge=1, le=100), search: str | None = None, _: dict = Depends(get_current_user)):
    query = {"$or": [{"name": {"$regex": search, "$options": "i"}}, {"code": {"$regex": search, "$options": "i"}}]} if search else {}
    return list_docs("sports", query, page, pageSize)


@router.get("/sports/{sport_id}", tags=["Sports"])
def get_sport(sport_id: str, _: dict = Depends(get_current_user)):
    return envelope(doc("sports", sport_id))


@router.post("/sports", status_code=201, tags=["Sports"])
def create_sport(payload: SportInput, _: dict = Depends(admin_only)):
    item = payload.model_dump(); item["createdAt"] = now(); item["updatedAt"] = now()
    try:
        result = collection("sports").insert_one(item)
    except DuplicateKeyError:
        raise HTTPException(409, "Sport code already exists")
    return envelope(doc("sports", str(result.inserted_id)), "Sport created successfully")


@router.patch("/sports/{sport_id}", tags=["Sports"])
def update_sport(sport_id: str, payload: SportPatch, _: dict = Depends(admin_only)):
    doc("sports", sport_id); changes = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}; changes["updatedAt"] = now()
    collection("sports").update_one({"_id": object_id(sport_id)}, {"$set": changes})
    return envelope(doc("sports", sport_id), "Sport updated successfully")


@router.get("/courses", tags=["Courses"])
def list_courses(page: int = Query(1, ge=1), pageSize: int = Query(20, ge=1, le=100), teacherId: str | None = None, studentId: str | None = None, search: str | None = None, _: dict = Depends(get_current_user)):
    query: dict[str, Any] = {}
    if teacherId: query["teacherId"] = teacherId
    if studentId: query["_id"] = {"$in": [object_id(x["courseId"]) for x in collection("enrollments").find({"userId": studentId})]}
    if search: query["$or"] = [{"name": {"$regex": search, "$options": "i"}}, {"code": {"$regex": search, "$options": "i"}}]
    return list_docs("courses", query, page, pageSize)


@router.get("/courses/{course_id}", tags=["Courses"])
def get_course(course_id: str, _: dict = Depends(get_current_user)):
    return envelope(doc("courses", course_id))


@router.post("/courses", status_code=201, tags=["Courses"])
def create_course(payload: CourseInput, _: dict = Depends(admin_or_teacher)):
    item = payload.model_dump(); item["studentTotal"] = 0; item["createdAt"] = now(); item["updatedAt"] = now()
    result = collection("courses").insert_one(item)
    return envelope(doc("courses", str(result.inserted_id)), "Course created successfully")


@router.patch("/courses/{course_id}", tags=["Courses"])
def update_course(course_id: str, payload: CoursePatch, _: dict = Depends(admin_or_teacher)):
    doc("courses", course_id); changes = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}; changes["updatedAt"] = now()
    collection("courses").update_one({"_id": object_id(course_id)}, {"$set": changes})
    return envelope(doc("courses", course_id), "Course updated successfully")


@router.delete("/courses/{course_id}", tags=["Courses"])
def delete_course(course_id: str, _: dict = Depends(admin_only)):
    doc("courses", course_id); collection("courses").delete_one({"_id": object_id(course_id)}); collection("tasks").delete_many({"courseId": course_id}); collection("enrollments").delete_many({"courseId": course_id})
    return {"message": "Course deleted successfully"}


@router.get("/courses/{course_id}/tasks", tags=["Tasks"])
def list_tasks(course_id: str, mode: str | None = None, sportId: str | None = None, page: int = Query(1, ge=1), pageSize: int = Query(20, ge=1, le=100), _: dict = Depends(get_current_user)):
    doc("courses", course_id); query: dict[str, Any] = {"courseId": course_id}
    if mode: query["mode"] = mode
    if sportId: query["sportId"] = sportId
    return list_docs("tasks", query, page, pageSize)


@router.get("/tasks/{task_id}", tags=["Tasks"])
def get_task(task_id: str, _: dict = Depends(get_current_user)):
    item = doc("tasks", task_id); item["sport"] = doc("sports", item["sportId"]); return envelope(item)


@router.post("/courses/{course_id}/tasks", status_code=201, tags=["Tasks"])
def create_task(course_id: str, payload: TaskInput, _: dict = Depends(admin_or_teacher)):
    doc("courses", course_id); doc("sports", payload.sportId); validate_task(payload.mode, payload.cameraId)
    item = payload.model_dump(); item["courseId"] = course_id; item["createdAt"] = now(); item["updatedAt"] = now(); result = collection("tasks").insert_one(item)
    return envelope(doc("tasks", str(result.inserted_id)), "Task created successfully")


@router.patch("/tasks/{task_id}", tags=["Tasks"])
def update_task(task_id: str, payload: TaskPatch, _: dict = Depends(admin_or_teacher)):
    item = doc("tasks", task_id); changes = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}; mode = changes.get("mode", item["mode"]); camera_id = changes.get("cameraId", item.get("cameraId")); validate_task(mode, camera_id); changes["updatedAt"] = now()
    collection("tasks").update_one({"_id": object_id(task_id)}, {"$set": changes}); return envelope(doc("tasks", task_id), "Task updated successfully")


@router.delete("/tasks/{task_id}", tags=["Tasks"])
def delete_task(task_id: str, _: dict = Depends(admin_or_teacher)):
    doc("tasks", task_id); collection("tasks").delete_one({"_id": object_id(task_id)}); return {"message": "Task deleted successfully"}


@router.get("/courses/{course_id}/students", tags=["Enrollment"])
def course_students(course_id: str, page: int = Query(1, ge=1), pageSize: int = Query(20, ge=1, le=100), search: str | None = None, status_filter: str | None = Query(None, alias="status"), _: dict = Depends(admin_or_teacher)):
    doc("courses", course_id); enrollments = [clean(x) for x in collection("enrollments").find({"courseId": course_id})]; users = []
    for enrollment in enrollments:
        try: user = clean(collection("users").find_one({"_id": object_id(enrollment["userId"])}))
        except ValueError: user = None
        if user and (not search or search.lower() in str(user.get("name", user.get("username", ""))).lower()): users.append({"userId": enrollment["userId"], "name": user.get("name", user.get("username", "")), "studentCode": user.get("studentCode"), "status": enrollment.get("status", "active"), "progressPercent": enrollment.get("progressPercent", 0)})
    if status_filter: users = [x for x in users if x["status"] == status_filter]
    return page_result(users[(page - 1) * pageSize:page * pageSize], page, pageSize, len(users))


@router.post("/courses/{course_id}/enrollments", status_code=201, tags=["Enrollment"])
def enroll(course_id: str, payload: EnrollmentInput, _: dict = Depends(admin_or_teacher)):
    course = doc("courses", course_id); doc("users", payload.userId); item = {"courseId": course_id, "userId": payload.userId, "status": "active", "progressPercent": 0, "completedTaskIds": [], "taskScores": {}, "createdAt": now()}
    try: collection("enrollments").insert_one(item)
    except DuplicateKeyError: raise HTTPException(409, "Student is already enrolled")
    collection("courses").update_one({"_id": object_id(course_id)}, {"$inc": {"studentTotal": 1}}); return envelope(clean(collection("enrollments").find_one({"courseId": course_id, "userId": payload.userId})), "Student enrolled successfully")


@router.delete("/courses/{course_id}/enrollments/{user_id}", tags=["Enrollment"])
def remove_enrollment(course_id: str, user_id: str, _: dict = Depends(admin_or_teacher)):
    result = collection("enrollments").delete_one({"courseId": course_id, "userId": user_id})
    if not result.deleted_count: raise HTTPException(404, "Enrollment not found")
    collection("courses").update_one({"_id": object_id(course_id)}, {"$inc": {"studentTotal": -1}}); return {"message": "Student removed successfully"}


@router.get("/enrollments/my-courses", tags=["Enrollment"])
def my_courses(user: dict = Depends(get_current_user)):
    user_id = user["id"]
    rows = []
    for enrollment in collection("enrollments").find({"userId": user_id}):
        try:
            course = clean(collection("courses").find_one({"_id": object_id(enrollment["courseId"])}))
        except ValueError:
            course = None
        if course:
            rows.append({
                "id": str(course["id"]),
                "courseId": str(course["id"]),
                "courseName": course.get("name"),
                "teacherName": course.get("teacherName"),
                "status": enrollment.get("status", "active"),
                "progressPercent": enrollment.get("progressPercent", 0),
                "examDate": course.get("examDate"),
                "grades": enrollment.get("grades", {}),
            })
    return envelope({"items": rows, "total": len(rows)})


@router.get("/teacher/courses", tags=["Teacher"])
def get_teacher_courses(user: dict = Depends(admin_or_teacher)):
    query = {}
    if user.get("role") == "teacher":
        query = {"teacherId": user["id"]}
    courses = [clean(c) for c in collection("courses").find(query)]
    if not courses and user.get("role") == "teacher":
        courses = [clean(c) for c in collection("courses").find({})]
    for c in courses:
        c["allowPracticeSubmission"] = True
        c["allowExamSubmission"] = True
        c["isGradeLocked"] = False
        c["studentTotal"] = collection("enrollments").count_documents({"courseId": str(c["id"])})
    return envelope(courses)


@router.get("/teacher/courses/{course_id}/gradebook", tags=["Teacher"])
def get_teacher_gradebook(course_id: str, _: dict = Depends(admin_or_teacher)):
    course = doc("courses", course_id)
    tasks = [clean(t) for t in collection("tasks").find({"courseId": course_id})]
    enrollments = [clean(e) for e in collection("enrollments").find({"courseId": course_id})]
    students = []
    for e in enrollments:
        try:
            u = clean(collection("users").find_one({"_id": object_id(e["userId"])}))
        except ValueError:
            u = None
        if u:
            user_submissions = {}
            for t in tasks:
                t_id = str(t["id"])
                sub = collection("video_results").find_one({"taskId": t_id, "userId": e["userId"]}, sort=[("submittedAt", -1)])
                if sub:
                    sub_clean = clean(sub)
                    user_submissions[t_id] = {
                        "videoUrl": sub_clean.get("videoUrl"),
                        "aiScore": sub_clean.get("aiScore"),
                        "teacherScore": sub_clean.get("finalScore"),
                        "teacherComment": sub_clean.get("teacherComment"),
                        "submittedAt": sub_clean.get("submittedAt"),
                        "metrics": sub_clean.get("metrics", {}),
                    }
            students.append({
                "userId": e["userId"],
                "studentCode": u.get("studentCode") or u.get("userCode") or u.get("username"),
                "studentName": u.get("name", u.get("username", "")),
                "progressPercent": e.get("progressPercent", 0),
                "taskScores": e.get("taskScores", {}),
                "grades": e.get("grades", {}),
                "submissions": user_submissions,
            })
    return envelope({
        "course": course,
        "taskList": tasks,
        "students": students,
    })


@router.get("/students/{user_id}/courses", tags=["Enrollment"])
def student_courses(user_id: str, _: dict = Depends(get_current_user)):
    rows = []
    for enrollment in collection("enrollments").find({"userId": user_id}):
        course = clean(collection("courses").find_one({"_id": object_id(enrollment["courseId"])}))
        if course: rows.append({"courseId": enrollment["courseId"], "courseName": course.get("name"), "teacherName": course.get("teacherName"), "status": enrollment.get("status"), "progressPercent": enrollment.get("progressPercent", 0), "examDate": course.get("examDate")})
    return envelope(rows)


@router.get("/courses/{course_id}/progress/{user_id}", tags=["Enrollment"])
def progress(course_id: str, user_id: str, _: dict = Depends(get_current_user)):
    item = collection("enrollments").find_one({"courseId": course_id, "userId": user_id})
    if not item: raise HTTPException(404, "Enrollment not found")
    item = clean(item); return envelope({"courseId": course_id, "userId": user_id, "progressPercent": item.get("progressPercent", 0), "completedTaskIds": item.get("completedTaskIds", []), "taskScores": item.get("taskScores", {})})


@router.post("/tasks/{task_id}/video-results", status_code=202, tags=["Video"])
def submit_video(task_id: str, video: UploadFile = File(...), attemptNo: int = 1, durationSec: int | None = None, user: dict = Depends(get_current_user)):
    task = doc("tasks", task_id)
    if task["mode"] != "video": raise HTTPException(400, "Task is not a video task")
    upload_dir = Path(settings.UPLOAD_DIR); upload_dir.mkdir(parents=True, exist_ok=True); target = upload_dir / f"{object_id(task_id)}-{datetime.now(timezone.utc).timestamp()}-{video.filename}"
    target.write_bytes(video.file.read()); item = {"taskId": task_id, "sportId": task["sportId"], "userId": user["id"], "attemptNo": attemptNo, "submittedAt": now(), "pending": True, "videoUrl": f"{settings.PUBLIC_BASE_URL}/{target.as_posix()}", "durationSec": durationSec, "metrics": {}, "aiScore": None, "aiComment": None, "finalScore": None, "teacherComment": None}
    result = collection("video_results").insert_one(item); return envelope(clean(collection("video_results").find_one({"_id": result.inserted_id})), "Video submitted successfully")


@router.get("/video-results/{result_id}", tags=["Video"])
def get_video_result(result_id: str, _: dict = Depends(get_current_user)):
    return envelope(doc("video_results", result_id))


@router.get("/tasks/{task_id}/video-results", tags=["Video"])
def task_video_results(task_id: str, userId: str | None = None, pending: bool | None = None, page: int = Query(1, ge=1), pageSize: int = Query(20, ge=1, le=100), _: dict = Depends(admin_or_teacher)):
    query: dict[str, Any] = {"taskId": task_id};
    if userId: query["userId"] = userId
    if pending is not None: query["pending"] = pending
    return list_docs("video_results", query, page, pageSize)


@router.get("/students/{user_id}/video-results", tags=["Video"])
def student_video_results(user_id: str, courseId: str | None = None, taskId: str | None = None, sportId: str | None = None, page: int = Query(1, ge=1), pageSize: int = Query(20, ge=1, le=100), _: dict = Depends(get_current_user)):
    query: dict[str, Any] = {"userId": user_id}
    if taskId: query["taskId"] = taskId
    if sportId: query["sportId"] = sportId
    if courseId: query["taskId"] = {"$in": [str(x["_id"]) for x in collection("tasks").find({"courseId": courseId}, {"_id": 1})]}
    return list_docs("video_results", query, page, pageSize)


@router.post("/video-results/{result_id}/retry", tags=["Video"])
def retry_video(result_id: str, _: dict = Depends(get_current_user)):
    doc("video_results", result_id); collection("video_results").update_one({"_id": object_id(result_id)}, {"$set": {"pending": True}}); return envelope({"id": result_id, "pending": True}, "Video processing has been queued again")


@router.patch("/video-results/{result_id}/grade", tags=["Grading"])
def grade_video(result_id: str, payload: GradeVideoInput, user: dict = Depends(admin_or_teacher)):
    doc("video_results", result_id); collection("video_results").update_one({"_id": object_id(result_id)}, {"$set": {**payload.model_dump(), "gradedBy": user["id"], "gradedAt": now(), "pending": False}}); return envelope(doc("video_results", result_id), "Result graded successfully")


@router.post("/tasks/{task_id}/live-results", status_code=201, tags=["Live"])
def start_live(task_id: str, payload: LiveInput, _: dict = Depends(get_current_user)):
    task = doc("tasks", task_id)
    if task["mode"] != "camera": raise HTTPException(400, "Task is not a camera task")
    item = {"taskId": task_id, "sportId": task["sportId"], "userId": payload.userId, "cameraId": task["cameraId"], "startedAt": now(), "completedAt": None, "metrics": {}, "score": None}
    result = collection("live_results").insert_one(item); return envelope(clean(collection("live_results").find_one({"_id": result.inserted_id})), "Live assessment started")


@router.patch("/live-results/{result_id}", tags=["Live"])
def update_live(result_id: str, payload: LivePatch, _: dict = Depends(get_current_user)):
    doc("live_results", result_id); changes = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}; collection("live_results").update_one({"_id": object_id(result_id)}, {"$set": changes}); return envelope(doc("live_results", result_id), "Live assessment updated")


@router.get("/live-results/{result_id}", tags=["Live"])
def get_live(result_id: str, _: dict = Depends(get_current_user)):
    return envelope(doc("live_results", result_id))


@router.patch("/live-results/{result_id}/grade", tags=["Grading"])
def grade_live(result_id: str, payload: GradeLiveInput, user: dict = Depends(admin_or_teacher)):
    doc("live_results", result_id); collection("live_results").update_one({"_id": object_id(result_id)}, {"$set": {**payload.model_dump(), "gradedBy": user["id"], "gradedAt": now()}}); return envelope(doc("live_results", result_id), "Live result finalized successfully")


@router.get("/cameras", tags=["Cameras"])
def list_cameras(status_filter: str | None = Query(None, alias="status"), page: int = Query(1, ge=1), pageSize: int = Query(20, ge=1, le=100), _: dict = Depends(get_current_user)):
    return list_docs("cameras", {"status": status_filter} if status_filter else {}, page, pageSize)


@router.get("/cameras/{camera_id}", tags=["Cameras"])
def get_camera(camera_id: str, _: dict = Depends(get_current_user)):
    return envelope(doc("cameras", camera_id))


@router.post("/cameras", status_code=201, tags=["Cameras"])
def create_camera(payload: CameraInput, _: dict = Depends(admin_only)):
    result = collection("cameras").insert_one({**payload.model_dump(), "createdAt": now(), "updatedAt": now()}); return envelope(doc("cameras", str(result.inserted_id)), "Camera created successfully")


@router.patch("/cameras/{camera_id}", tags=["Cameras"])
def update_camera(camera_id: str, payload: CameraPatch, _: dict = Depends(admin_only)):
    doc("cameras", camera_id); collection("cameras").update_one({"_id": object_id(camera_id)}, {"$set": {**{k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}, "updatedAt": now()}}); return envelope(doc("cameras", camera_id), "Camera updated successfully")


@router.delete("/cameras/{camera_id}", tags=["Cameras"])
def delete_camera(camera_id: str, _: dict = Depends(admin_only)):
    doc("cameras", camera_id)
    if collection("tasks").find_one({"cameraId": camera_id, "mode": "camera"}): raise HTTPException(409, "Camera is still referenced by a task")
    collection("cameras").delete_one({"_id": object_id(camera_id)}); return {"message": "Camera deleted successfully"}
