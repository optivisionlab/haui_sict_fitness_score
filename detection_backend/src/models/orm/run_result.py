from sqlalchemy import Column, Integer, String, TIMESTAMP
from src.models.orm.base import Base


class RedisResults(Base):
    __tablename__ = "redisresults"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False)
    exam_id = Column(String)
    step = Column(Integer, nullable=False)
    lap = Column(Integer, nullable=False)
    flag1 = Column(Integer)
    flag2 = Column(Integer)
    flag3 = Column(Integer)
    flag4 = Column(Integer)
    start_time = Column(TIMESTAMP(timezone=False), nullable=False)
    url = Column(String)

    def __repr__(self):
        return f"<RedisResults(id={self.id}, user_id={self.user_id}, exam_id={self.exam_id})>"

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "exam_id": self.exam_id,
            "step": self.step,
            "lap": self.lap,
            "flag1": self.flag1,
            "flag2": self.flag2,
            "flag3": self.flag3,
            "flag4": self.flag4,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "url": self.url,
        }