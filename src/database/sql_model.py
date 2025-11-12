from sqlmodel import SQLModel, Field, create_engine, Session, select
from datetime import datetime
from loguru import logger



# --- Định nghĩa model ORM ---
class Results(SQLModel, table=True):
    result_id: int | None = Field(default=None, primary_key=True)
    user_id: str
    exam_id: str | None = None
    step: int
    start_time: datetime
    end_time: datetime
    created_at: datetime
    updated_at: datetime



# --- Handler ---
class PostgresHandler:
    def __init__(self, dsn: str):
        self.engine = create_engine(dsn, echo=False)
        
        # Tạo bảng nếu chưa có
        SQLModel.metadata.create_all(self.engine)


    def insert_lap(self, user_id, lap_number, start_time, end_time, exam_id, created_at, updated_at, result_id):
        with Session(self.engine) as session:
            lap = Results(
                user_id=user_id,
                exam_id=exam_id,
                lap_number=lap_number,
                start_time=start_time,
                end_time=end_time,
                created_at=created_at,
                updated_at=updated_at,
                result_id=result_id
            )
            session.add(lap)
            session.commit()


    def get_last_lap(self, user_id: str):
        with Session(self.engine) as session:
            statement = select(Results).where(Results.user_id == user_id).order_by(Results.lap_number.desc())
            result = session.exec(statement).first()
            return result

    def update_velocity(self, lap_id: int, new_velocity: float):
        with Session(self.engine) as session:
            lap = session.get(Results, lap_id)
            if lap:
                lap.velocity = new_velocity
                session.add(lap)
                session.commit()
                logger.info(f"📝 Cập nhật velocity={new_velocity} cho lap_id={lap_id}")
            else:
                logger.warning(f"⚠️ Không tìm thấy lap_id={lap_id}")

    def delete_lap(self, lap_id: int):
        with Session(self.engine) as session:
            lap = session.get(Results, lap_id)
            if lap:
                session.delete(lap)
                session.commit()
                logger.info(f"🗑️ Xóa bản ghi lap_id={lap_id}")
            else:
                logger.warning(f"⚠️ Không tìm thấy lap_id={lap_id}")
