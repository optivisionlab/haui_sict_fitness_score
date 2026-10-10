# Lab Fitness API — AI Sport Scoring & LMS Backend

Hệ thống Backend FastAPI quản lý đào tạo thể chất và chấm điểm tự động bằng AI qua 2 hình thức: **Video nộp bài** và **Camera trực tiếp tại sân**.

Hệ thống được thiết kế theo kiến trúc Microservices / Event-Driven hỗ trợ xử lý bất đồng bộ qua **Kafka Message Broker**, lưu trữ media tập trung trên **MinIO (S3 Compatible)**, bộ nhớ đệm **Redis**, và cơ sở dữ liệu **MongoDB**.

---

## 🛠️ Yêu cầu môi trường

- **Docker & Docker Compose** (v2.x trở lên)
- **Python**: 3.11+
- **Git**

---

## 🚀 Hướng dẫn khởi chạy nhanh

### Bước 1: Sao chép biến môi trường
Clone repository và tạo file `.env` từ `.env.example`:

```bash
# Windows PowerShell
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

---

### Bước 2: Lựa chọn cách khởi chạy

#### 🔹 Cách 1: Khởi chạy toàn bộ bằng Docker Compose (Khuyên dùng khi triển khai/test nhanh)
Khởi động tất cả các dịch vụ (MongoDB, Redis, MinIO, Kafka, Kafka UI và Backend API) chỉ với 1 câu lệnh:

```bash
docker compose up -d --build
```

Kiểm tra trạng thái các container:
```bash
docker compose ps
```

---

#### 🔹 Cách 2: Khởi chạy hạ tầng Docker + Chạy Backend local (Phù hợp khi code/debug)

1. **Khởi chạy hạ tầng dịch vụ (MongoDB, Redis, MinIO, Kafka, Kafka UI):**
```bash
docker compose up -d mongodb redis minio kafka kafka-ui
```

2. **Cài đặt môi trường Python & dependencies:**
```powershell
# Tạo và kích hoạt môi trường ảo
python -m venv venv
.\venv\Scripts\activate   # Trên Windows
# source venv/bin/activate # Trên Linux / macOS

# Cài đặt thư viện
pip install -r requirements.txt
```

3. **Kiểm tra kết nối các dịch vụ:**
```bash
python scripts/test_connection.py
```

4. **Khởi chạy FastAPI Server (Hot Reload):**
```bash
uvicorn app.main:app --reload --port 8000
```

---

### Bước 3: Nạp dữ liệu mẫu (Seed Data)

Nạp dữ liệu người dùng, môn học, bài tập và video demo chuẩn vào hệ thống:

```bash
python scripts/seed_data.py
```

*Muốn làm sạch dữ liệu cũ và nạp mới hoàn toàn:*
```bash
python scripts/seed_data.py --clean
```

---

## 🌐 Các cổng dịch vụ & Giao diện quản trị

| Dịch vụ | Địa chỉ truy cập | Ghi chú / Tài khoản mặc định |
| :--- | :--- | :--- |
| **FastAPI Swagger Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) | Tài liệu OpenAPI tương tác |
| **FastAPI ReDoc** | [http://localhost:8000/redoc](http://localhost:8000/redoc) | Giao diện tài liệu API dự phòng |
| **MinIO Console** | [http://localhost:9001](http://localhost:9001) | User: `admin` / Pass: `password123` |
| **MinIO S3 API** | [http://localhost:9000](http://localhost:9000) | Endpoint upload/download file |
| **Kafka UI** | [http://localhost:8080](http://localhost:8080) | Quản lý topics & consumer groups |
| **Kafka Broker** | `localhost:9092` (Local) / `kafka:9093` (Docker) | Cụm tin nhắn KRaft |
| **Redis** | `localhost:6379` | Mật khẩu: `optivisionlab` |
| **MongoDB** | `localhost:27017` | User: `admin` / Pass: `123456` |
| **Mongo Express** | [http://localhost:8081](http://localhost:8081) | Web UI quản lý MongoDB trực quan |

---

## 🔑 Tài khoản kiểm thử có sẵn

Mật khẩu mặc định cho toàn bộ tài khoản thử nghiệm: **`123456`**

- **Admin:** `admin@university.edu.vn`
- **Giáo viên:** `teacher@university.edu.vn`
- **Sinh viên:** `student1@university.edu.vn`, `student2@university.edu.vn`, ...

---

## 🧪 Kiểm thử hệ thống (Automated Tests)

Chạy các bộ kiểm thử tự động để đảm bảo tính toàn vẹn logic:

```bash
# 1. Kiểm thử logic tính điểm & Schema
python scripts/test_unit.py

# 2. Kiểm thử các lớp bảo vệ nộp bài (Guards)
python scripts/test_guards.py

# 3. Kiểm thử luồng Kafka Producer/Consumer
python scripts/test_kafka_flow.py
```

---

## 🤖 Kết nối Mô hình AI chấm điểm (AI Worker)

Backend phát hành và lắng nghe các sự kiện chấm điểm qua Kafka:
- **Topic nhận yêu cầu chấm điểm:** `video-grading-jobs` (Backend gửi sang cho Model AI)
- **Topic nhận kết quả chấm điểm:** `video-grading-results` (Model AI gửi kết quả về cho Backend cập nhật DB)
- **Topic lỗi (DLQ):** `video-grading-dlq`
