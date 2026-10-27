from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from pymongo import ReturnDocument

from app.crud.base import to_object_id
from app.crud.camera import crud_camera
from app.crud.course import crud_course
from app.crud.sport import crud_sport
from app.crud.task import crud_task
from app.crud.video_result import crud_video_result
from app.models.sport import SportMode
from app.models.task import Task, TaskCategory
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate


class TaskService:
    def create_task(self, task_in: TaskCreate) -> Task:
        """Tạo bài tập / bài thi mới."""
        course = crud_course.get(task_in.course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy khóa học ID {task_in.course_id}",
            )

        sport = crud_sport.get(task_in.sport_id)
        if not sport:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy môn thể thao ID {task_in.sport_id}",
            )

        if sport.mode == SportMode.CAMERA:
            if not task_in.camera_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Môn thể thao hình thức camera bắt buộc phải chọn camera_id",
                )
            camera = crud_camera.get(task_in.camera_id)
            if not camera:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Không tìm thấy thiết bị camera ID {task_in.camera_id}",
                )

        return crud_task.create(task_in)

    def get_by_id(self, task_id: str) -> Task:
        """Lấy chi tiết task."""
        task = crud_task.get(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy bài tập/bài thi",
            )
        return task

    def list_tasks(
        self,
        course_id: Optional[str] = None,
        sport_id: Optional[str] = None,
        category: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Task], int]:
        """Lấy danh sách task có hỗ trợ lọc theo category (practice / exam)."""
        query: dict = {}
        if course_id:
            query["courseId"] = str(course_id)
        if sport_id:
            query["sportId"] = str(sport_id)
        if category and category != "all":
            query["category"] = category

        return crud_task.get_multi(filter=query, skip=skip, limit=limit)

    def update_task(self, task_id: str, task_in: TaskUpdate) -> Task:
        """Cập nhật thông tin task."""
        self.get_by_id(task_id)

        if task_in.course_id and not crud_course.exists(task_in.course_id):
            raise HTTPException(status_code=404, detail="Khóa học không tồn tại")
        if task_in.sport_id and not crud_sport.exists(task_in.sport_id):
            raise HTTPException(status_code=404, detail="Môn thể thao không tồn tại")
        if task_in.camera_id and not crud_camera.exists(task_in.camera_id):
            raise HTTPException(status_code=404, detail="Camera không tồn tại")

        updated = crud_task.update(task_id, task_in)
        if not updated:
            raise HTTPException(status_code=400, detail="Cập nhật bài tập thất bại")
        return updated

    def toggle_lock(self, task_id: str, is_locked: bool) -> Task:
        """Khóa hoặc mở khóa nhanh một bài tập cụ thể."""
        self.get_by_id(task_id)
        obj_id = to_object_id(task_id)
        if not obj_id:
            raise HTTPException(status_code=400, detail="Mã bài tập không hợp lệ")

        updated = crud_task.collection.find_one_and_update(
            {"_id": obj_id},
            {"$set": {"isLocked": is_locked}},
            return_document=ReturnDocument.AFTER,
        )
        return Task.model_validate(updated)

    def delete_task(self, task_id: str) -> bool:
        """Xóa task."""
        self.get_by_id(task_id)
        return crud_task.delete(task_id)

    def to_read_dto(self, task: Task) -> TaskRead:
        """Chuyển đổi Task entity sang TaskRead DTO kèm thông tin sport và số lượng bài nộp."""
        return self.to_read_dtos([task])[0]

    def to_read_dtos(self, tasks: list[Task]) -> list[TaskRead]:
        """Như to_read_dto cho cả danh sách: 1 truy vấn sport + 1 aggregate đếm bài nộp
        (trước đây mỗi task tốn 3 truy vấn)."""
        if not tasks:
            return []
        sport_ids = {to_object_id(t.sport_id) for t in tasks if to_object_id(t.sport_id)}
        sports = {
            str(doc["_id"]): doc
            for doc in crud_sport.collection.find({"_id": {"$in": list(sport_ids)}}, {"name": 1, "mode": 1})
        }
        task_ids = [str(t.id) for t in tasks]
        counts = {
            row["_id"]: row
            for row in crud_video_result.collection.aggregate([
                {"$match": {"taskId": {"$in": task_ids}}},
                {"$group": {
                    "_id": "$taskId",
                    "submitted": {"$sum": 1},
                    # Cùng điều kiện với bản cũ: pending == False hoặc finalScore khác null
                    "graded": {"$sum": {"$cond": [
                        {"$or": [
                            {"$eq": ["$pending", False]},
                            {"$ne": [{"$ifNull": ["$finalScore", None]}, None]},
                        ]},
                        1, 0,
                    ]}},
                }},
            ])
        }
        dtos = []
        for task in tasks:
            sport = sports.get(str(task.sport_id))
            row = counts.get(str(task.id), {})
            dto_data = task.model_dump()
            dto_data["sport_name"] = sport.get("name") if sport else None
            mode = sport.get("mode") if sport else None
            dto_data["sport_mode"] = getattr(mode, "value", mode)
            dto_data["submitted_count"] = row.get("submitted", 0)
            dto_data["graded_count"] = row.get("graded", 0)
            dtos.append(TaskRead.model_validate(dto_data))
        return dtos


task_service = TaskService()
