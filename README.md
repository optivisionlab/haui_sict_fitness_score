# Fitness Score API

Hướng dẫn nhanh để thiết lập và chạy project "Fitness Score API" (FastAPI).

## Yêu cầu
- Python 3.10+
- git
- Kết nối PostgreSQL
- Kết nối Redis
## 1) Clone repository

Mở terminal và chạy:

```bash
git clone git clone --branch cuongdev --single-branch git@github.com:optivisionlab/haui_sict_fitness_score.git
cd haui_sict_fitness_score
```

## 2) Tạo và kích hoạt môi trường ảo (virtual environment)

Trên Linux/macOS:

```bash
python3.10 -m venv .venv
source .venv/bin/activate
```

Trên Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Sau khi kích hoạt, nâng cấp pip:

```bash
pip install --upgrade pip
```

## 3) Cài đặt phụ thuộc

```bash
pip install -r requirements.txt
```

## 4) Tạo file `.env`

Tạo một file `.env` ở thư mục gốc của repo với nội dung tương tự:

```env
POSTGRES_USER=you
POSTGRES_PASSWORD=your_password
POSTGRES_SERVER=your_server
POSTGRES_PORT=your_port
POSTGRES_DB=yourdb

SECRET_KEY=your_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

Lưu ý:
- Thay giá trị bằng thông tin thực tế (đặc biệt `POSTGRES_PASSWORD` và `SECRET_KEY`).

### Về `DATABASE_URL` trong `app/core/config.py`
Trong file `app/core/config.py`, thuộc tính `DATABASE_URL` hiện đang trả về một chuỗi kết nối cứng (hard-coded). Nếu bạn muốn sử dụng các biến `POSTGRES_*` từ `.env`, bạn có thể sửa dòng trong `DATABASE_URL` để dùng:

## 5) Chạy ứng dụng (development)

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
- Health check: http://localhost:8000/health
- Root: http://localhost:8000/
- Swagger UI (interactive docs): http://localhost:8000/docs
- OpenAPI JSON: http://localhost:8000/api/v1/openapi.json

Ghi chú: `api/v1` là prefix API theo cấu hình (`settings.API_V1_STR`).

