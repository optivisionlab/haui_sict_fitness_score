from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker
from src.models.orm.base import Base


class Student(Base):
    __tablename__ = "students"
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}


    StudentID = Column(Integer, primary_key=True, autoincrement=True)
    Name = Column(String(255), nullable=False)
    DOB = Column(DateTime, nullable=False)
    Class = Column(String(100), nullable=False)
    PhoneNumber = Column(String(20))

    def __repr__(self):
        return f"<Student(ID={self.StudentID}, Name='{self.Name}', Class='{self.Class}')>"