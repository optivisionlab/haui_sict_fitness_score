from typing import Optional

from app.crud.base import CRUDBase
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate


class CRUDTask(CRUDBase[Task, TaskCreate, TaskUpdate]):
    def get_by_course(
        self,
        course_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Task], int]:
        """Lấy danh sách các bài tập / bài thi thuộc về một khóa học."""
        return self.get_multi(filter={"courseId": str(course_id)}, skip=skip, limit=limit)

    def get_by_sport(
        self,
        sport_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Task], int]:
        """Lấy danh sách bài tập thuộc về một môn thể thao."""
        return self.get_multi(filter={"sportId": str(sport_id)}, skip=skip, limit=limit)

    def get_by_camera(
        self,
        camera_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Task], int]:
        """Lấy danh sách các bài thi liên kết với camera này."""
        return self.get_multi(filter={"cameraId": str(camera_id)}, skip=skip, limit=limit)


crud_task = CRUDTask(Task)
