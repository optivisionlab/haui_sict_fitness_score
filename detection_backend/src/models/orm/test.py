from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.models.orm.base import Base
from src.models.orm.student import Student
from src.models.orm.subject import Subject

DB_USER = "root"
DB_PASS = "test"
DB_HOST = "localhost"
DB_PORT = 3306
DB_NAME = "school_db"

engine_tmp = create_engine(f"mysql+mysqlconnector://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}")

with engine_tmp.connect() as conn:
    conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}"))
    conn.commit()


DATABASE_URL = (
    "mysql+mysqlconnector://root:test@localhost:3306/school_db"
    #"postgresql+psycopg2://postgres:password@localhost:5432/school_db" Trong trường hợp dùng postgresql
)

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine)

Base.metadata.create_all(engine)

session = SessionLocal()

new_student = Student(
    Name="Chu Huy Hoàng",
    DOB=datetime(2000, 5, 12),
    Class="AI-01"
)

new_subject = Subject(
    Name="Nhập môn OOP",
    Credit=10,
    NumberStudent=500
)

session.add(new_student)
session.add(new_subject)
session.commit()
session.close()
