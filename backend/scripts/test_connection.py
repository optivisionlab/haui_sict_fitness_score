"""
Script kiểm tra kết nối các dịch vụ trong .env:
- MongoDB
- Redis
- MinIO
"""

import os
import socket
import sys
import urllib.request
from pathlib import Path

# Đảm bảo UTF-8 trên Windows console
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Thêm thư mục gốc backend vào sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.core.database import _get_redis_kwargs
import pymongo
import redis


def check_port(host: str, port: int, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def test_mongodb():
    print("\n" + "=" * 50)
    print("1. KIỂM TRA MONGODB")
    print("=" * 50)
    uri = settings.MONGODB_URI
    db_name = settings.MONGODB_DB
    print(f"[*] URI: {uri}")
    print(f"[*] Database: {db_name}")

    try:
        client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=4000)
        # Ping server
        client.admin.command("ping")
        print("[OK] Kết nối MongoDB THÀNH CÔNG!")

        db = client[db_name]
        collections = db.list_collection_names()
        print(f"[OK] Đã truy cập Database '{db_name}'.")
        print(f"[*] Số lượng collections hiện có: {len(collections)}")
        if collections:
            print(f"[*] Danh sách collections: {', '.join(collections[:5])}" + ("..." if len(collections) > 5 else ""))
        else:
            print("[i] Database chưa có collection nào (có thể chạy 'python seed_data.py' để nạp dữ liệu mẫu).")
        return True
    except pymongo.errors.ServerSelectionTimeoutError as e:
        print(f"[ERROR] Không kết nối được tới MongoDB (Timeout sau 4s).")
        print(f"        Chi tiết: {e}")
        print("[!] GỢI Ý: Hãy kiểm tra:")
        print("    1. Máy chủ MongoDB có đang chạy không?")
        print("    2. Nếu dùng IP Tailscale (100.x.x.x), máy này và máy server đã bật Tailscale chưa?")
        print("    3. Nếu chạy MongoDB local, đổi MONGODB_URI=mongodb://localhost:27017 trong .env.")
        return False
    except Exception as e:
        print(f"[ERROR] Lỗi kết nối MongoDB: {e}")
        return False


def test_redis():
    print("\n" + "=" * 50)
    print("2. KIỂM TRA REDIS")
    print("=" * 50)
    kwargs = _get_redis_kwargs()
    print(f"[*] Host: {kwargs.get('host')}:{kwargs.get('port')}")
    print(f"[*] DB Index: {kwargs.get('db')}")
    print(f"[*] Có mật khẩu: {'Có' if kwargs.get('password') else 'Không'}")

    try:
        r = redis.Redis(**kwargs, socket_timeout=4.0, socket_connect_timeout=4.0)
        pong = r.ping()
        if pong:
            print("[OK] Kết nối Redis THÀNH CÔNG! (PING -> PONG)")
            # Thử set/get key test
            test_key = "__connection_test_key__"
            r.set(test_key, "ok", ex=10)
            val = r.get(test_key)
            if val == "ok" or val == b"ok":
                print("[OK] Thử nghiệm Ghi / Đọc Redis key thành công!")
            r.delete(test_key)
            return True
        else:
            print(f"[ERROR] Redis trả về: {pong}")
            return False
    except redis.exceptions.AuthenticationError:
        print("[ERROR] Mật khẩu Redis không chính xác (REDIS_PASSWORD).")
        return False
    except (redis.exceptions.TimeoutError, redis.exceptions.ConnectionError) as e:
        print(f"[ERROR] Không kết nối được tới Redis (Timeout / Connection Refused).")
        print(f"        Chi tiết: {e}")
        print("[!] GỢI Ý: Hãy kiểm tra:")
        print("    1. Redis Server có đang bật tại cổng 6379?")
        print("    2. Kiểm tra mạng / Tailscale nếu kết nối qua IP từ xa.")
        print("    3. Nếu chạy local, đổi REDIS_HOST=localhost trong .env.")
        return False
    except Exception as e:
        print(f"[ERROR] Lỗi kết nối Redis: {e}")
        return False


def test_minio():
    print("\n" + "=" * 50)
    print("3. KIỂM TRA MINIO")
    print("=" * 50)
    endpoint = settings.MINIO_ENDPOINT
    print(f"[*] Endpoint: {endpoint}")

    # Tách host và port
    parts = endpoint.replace("http://", "").replace("https://", "").split(":")
    host = parts[0]
    port = int(parts[1]) if len(parts) > 1 else 9000

    port_ok = check_port(host, port, timeout=3.0)
    if not port_ok:
        print(f"[ERROR] Không kết nối được tới MinIO tại {host}:{port} (Port đóng hoặc không phản hồi).")
        print("[!] GỢI Ý: Kiểm tra dịch vụ MinIO và trạng thái mạng/Tailscale.")
        return False

    print(f"[OK] Cổng MinIO {host}:{port} đang MỞ!")
    # Thử gọi health check HTTP
    url = f"http://{endpoint}/minio/health/live"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "HealthCheck"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            if resp.status == 200:
                print(f"[OK] MinIO Healthcheck live: 200 OK")
                return True
    except Exception as e:
        print(f"[i] Cổng mở nhưng endpoint HTTP /minio/health/live trả về: {e} (Có thể MinIO chạy sau proxy hoặc cần TLS)")
        return True


def test_kafka():
    print("\n" + "=" * 50)
    print("4. KIỂM TRA KAFKA BROKER")
    print("=" * 50)
    servers = settings.KAFKA_BOOTSTRAP_SERVERS
    print(f"[*] Bootstrap Servers: {servers}")
    parts = servers.split(":")
    host = parts[0]
    port = int(parts[1]) if len(parts) > 1 else 9092

    port_ok = check_port(host, port, timeout=3.0)
    if not port_ok:
        print(f"[ERROR] Không kết nối được tới Kafka Broker tại {host}:{port}.")
        return False

    print(f"[OK] Cổng Kafka Broker {host}:{port} đang MỞ!")
    return True


def main():
    print("==================================================")
    print("   KIỂM TRA CẤU HÌNH VÀ KẾT NỐI TỪ FILE .ENV")
    print("==================================================")
    
    mongo_ok = test_mongodb()
    redis_ok = test_redis()
    minio_ok = test_minio()
    kafka_ok = test_kafka()

    print("\n" + "=" * 50)
    print("TỔNG KẾT:")
    print(f"  - MongoDB : {'✅ KẾT NỐI ĐƯỢC' if mongo_ok else '❌ THẤT BẠI'}")
    print(f"  - Redis   : {'✅ KẾT NỐI ĐƯỢC' if redis_ok else '❌ THẤT BẠI'}")
    print(f"  - MinIO   : {'✅ KẾT NỐI ĐƯỢC' if minio_ok else '❌ THẤT BẠI'}")
    print(f"  - Kafka   : {'✅ KẾT NỐI ĐƯỢC' if kafka_ok else '❌ THẤT BẠI'}")
    print("=" * 50)


if __name__ == "__main__":
    main()

