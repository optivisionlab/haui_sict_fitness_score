from sqlalchemy import Column, Integer, String
from src.models.orm.base import Base

class Subject(Base):
    __tablename__ = "subject"
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}

    ID = Column(Integer, primary_key=True, autoincrement=True)
    Name = Column(String(255), nullable=False)
    Credit = Column(Integer, nullable=False)
    NumberStudent = Column(Integer, nullable=False)
