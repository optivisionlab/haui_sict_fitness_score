from sqlmodel import SQLModel, Field, create_engine, Session, select, UniqueConstraint
from datetime import datetime
from loguru import logger
from sqlalchemy import case, MetaData, Table
from sqlalchemy.dialects.postgresql import insert
from urllib.parse import quote_plus

# --- Định nghĩa model ORM ---
class Results(SQLModel, table=True):
    result_id: int | None = Field(default=None, primary_key=True)
    user_id: str
    exam_id: str | None = None
    step: int
    lap: int
    start_time: datetime
    end_time: datetime
    __table_args__ = (
            UniqueConstraint("user_id", "exam_id", "step", name="uq_user_exam_step"),
        )


class RedisResults(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: str
    exam_id: str | None = None
    step: int
    lap: int
    flag1: int | None = None
    flag2: int | None = None
    flag3: int | None = None
    flag4: int | None = None
    start_time: datetime
    url: str | None = None


# --- Handler ---
class PostgresHandler:
    def __init__(self, dsn: str):
        self.engine = create_engine(dsn, echo=False)
        
        # Tạo bảng nếu chưa có
        SQLModel.metadata.create_all(self.engine)


    def insert_redis(
        self, user_id, exam_id, step, lap, start_time,
        flag1=0, flag2=None, flag3=None, flag4=None,
        url=None, end_time=None
    ):
        meta = MetaData()
        results_table = Table("redisresults", meta, autoload_with=self.engine)

        insert_values = {
            "user_id": user_id,
            "exam_id": exam_id,
            "step": step,
            "lap": lap,
            "start_time": start_time,
            "flag1": flag1,
            "flag2": flag2,
            "flag3": flag3,
            "flag4": flag4,
            "url": url,
        }

        stmt = insert(results_table).values(insert_values)

        with self.engine.begin() as conn:
            conn.execute(stmt)


    def insert_or_update_lap(self, user_id, exam_id, step, lap_number, start_time, end_time=None):
        meta = MetaData()
        results_table = Table("results", meta, autoload_with=self.engine)

        stmt = insert(results_table).values(
            user_id=user_id,
            exam_id=exam_id,
            step=step,
            lap=lap_number,
            start_time=start_time,
            end_time=end_time
        )

        update_values = {
                "lap": lap_number,
            }

            # chỉ update end_time nếu được truyền vào
        if end_time is not None:
            update_values["end_time"] = end_time

        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id", "exam_id", "step"],
            set_=update_values,
        )

        with self.engine.begin() as conn:
            conn.execute(stmt)


    def delete_lap(self, lap_id: int):
        with Session(self.engine) as session:
            lap = session.get(Results, lap_id)
            if lap:
                session.delete(lap)
                session.commit()
                logger.info(f"🗑️ Xóa bản ghi lap_id={lap_id}")
            else:
                logger.warning(f"⚠️ Không tìm thấy lap_id={lap_id}")
