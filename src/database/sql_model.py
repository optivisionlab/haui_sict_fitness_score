from sqlmodel import SQLModel, Field, create_engine, Session, select
from datetime import datetime
from loguru import logger



# --- Định nghĩa model ORM ---
class LapHistory(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: str
    lap_number: int
    start_time: datetime
    end_time: datetime
    lap_duration: float
    velocity: float
    cam1_time: datetime
    cam2_time: datetime
    cam3_time: datetime
    cam4_time: datetime

# --- Handler ---
class PostgresHandler:
    def __init__(self, dsn: str):
        self.engine = create_engine(dsn, echo=False)
        
        # Tạo bảng nếu chưa có
        SQLModel.metadata.create_all(self.engine)


    def insert_lap(self, user_id, lap_number, start_time, end_time, lap_duration, velocity, cam_times: dict = None):
        with Session(self.engine) as session:
            lap = LapHistory(
                user_id=user_id,
                lap_number=lap_number,
                start_time=start_time,
                end_time=end_time,
                lap_duration=lap_duration,
                velocity=velocity,
                cam1_time=cam_times.get("1"),
                cam2_time=cam_times.get("2"),
                cam3_time=cam_times.get("3"),
                cam4_time=cam_times.get("4"),
            )
            session.add(lap)
            session.commit()


    def get_last_lap(self, user_id: str):
        with Session(self.engine) as session:
            statement = select(LapHistory).where(LapHistory.user_id == user_id).order_by(LapHistory.lap_number.desc())
            result = session.exec(statement).first()
            return result

    def update_velocity(self, lap_id: int, new_velocity: float):
        with Session(self.engine) as session:
            lap = session.get(LapHistory, lap_id)
            if lap:
                lap.velocity = new_velocity
                session.add(lap)
                session.commit()
                logger.info(f"📝 Cập nhật velocity={new_velocity} cho lap_id={lap_id}")
            else:
                logger.warning(f"⚠️ Không tìm thấy lap_id={lap_id}")

    def delete_lap(self, lap_id: int):
        with Session(self.engine) as session:
            lap = session.get(LapHistory, lap_id)
            if lap:
                session.delete(lap)
                session.commit()
                logger.info(f"🗑️ Xóa bản ghi lap_id={lap_id}")
            else:
                logger.warning(f"⚠️ Không tìm thấy lap_id={lap_id}")
