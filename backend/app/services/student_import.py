"""Import danh sách sinh viên vào lớp học phần từ file .xlsx hoặc .csv.

Cột nhận diện theo tiêu đề (không phân biệt hoa thường, có/không dấu):
  - Mã SV:  "Mã SV", "MSSV", "Mã sinh viên"
  - Email:  "Email"
  - Họ tên: "Họ tên", "Họ và tên" (chỉ để đối chiếu, không bắt buộc)
Chỉ ghi danh sinh viên đã có tài khoản; dòng chưa có tài khoản được báo lại để admin tạo trước.
"""
import csv
import io
import re
import unicodedata
import zipfile
from xml.etree import ElementTree

from fastapi import HTTPException

from app.crud.enrollment import crud_enrollment
from app.crud.user import crud_user
from app.models.user import UserRole
from app.schemas.enrollment import EnrollmentCreate
from app.schemas.teacher import StudentImportResult

MAX_IMPORT_ROWS = 2000
_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

HEADERS = {
    "code": {"masv", "mssv", "masinhvien", "usercode"},
    "name": {"hoten", "hovaten", "name", "fullname"},
    "email": {"email", "mail", "emailtruong"},
}


def _norm(text: str) -> str:
    text = str(text or "").lower().replace("đ", "d")
    text = unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", text)


def _col_index(ref: str) -> int:
    idx = 0
    for ch in re.match(r"[A-Z]+", ref).group():
        idx = idx * 26 + (ord(ch) - 64)
    return idx - 1


def _read_xlsx(data: bytes) -> list[list[str]]:
    """Đọc sheet đầu tiên của .xlsx bằng thư viện chuẩn (không cần openpyxl)."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=400, detail="File Excel không hợp lệ") from exc
    shared: list[str] = []
    if "xl/sharedStrings.xml" in zf.namelist():
        root = ElementTree.fromstring(zf.read("xl/sharedStrings.xml"))
        for si in root.findall("m:si", _NS):
            shared.append("".join(t.text or "" for t in si.iter(f"{{{_NS['m']}}}t")))
    sheet = next((n for n in sorted(zf.namelist()) if re.match(r"xl/worksheets/sheet\d+\.xml$", n)), None)
    if not sheet:
        raise HTTPException(status_code=400, detail="File Excel không có sheet dữ liệu")
    rows: list[list[str]] = []
    for row in ElementTree.fromstring(zf.read(sheet)).iter(f"{{{_NS['m']}}}row"):
        values: dict[int, str] = {}
        for cell in row.findall("m:c", _NS):
            kind, ref = cell.get("t"), cell.get("r", "A1")
            if kind == "inlineStr":
                text = "".join(t.text or "" for t in cell.iter(f"{{{_NS['m']}}}t"))
            else:
                v = cell.find("m:v", _NS)
                text = v.text if v is not None and v.text is not None else ""
                if kind == "s" and text.isdigit():
                    text = shared[int(text)] if int(text) < len(shared) else ""
                elif re.fullmatch(r"\d+\.0", text):
                    text = text[:-2]  # mã SV dạng số được lưu thành 2022601001.0
            values[_col_index(ref)] = text.strip()
        if values:
            rows.append([values.get(i, "") for i in range(max(values) + 1)])
    return rows


def _read_csv(data: bytes) -> list[list[str]]:
    text = data.decode("utf-8-sig", errors="replace")
    try:
        dialect = csv.Sniffer().sniff(text[:2048], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    return [[c.strip() for c in row] for row in csv.reader(io.StringIO(text), dialect)]


def parse_rows(filename: str, data: bytes) -> list[tuple[int, dict[str, str]]]:
    name = (filename or "").lower()
    if name.endswith(".xlsx"):
        rows = _read_xlsx(data)
    elif name.endswith(".csv"):
        rows = _read_csv(data)
    else:
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ file .xlsx hoặc .csv")

    # Dòng tiêu đề nằm trong 10 dòng đầu, cần có cột Mã SV hoặc Email
    cols: dict[str, int] = {}
    header_idx = -1
    for i, row in enumerate(rows[:10]):
        found: dict[str, int] = {}
        for c, cell in enumerate(row):
            key = _norm(cell)
            for field, names in HEADERS.items():
                if key in names and field not in found:
                    found[field] = c
        if "code" in found or "email" in found:
            cols, header_idx = found, i
            break
    if header_idx < 0:
        raise HTTPException(status_code=400, detail="Không tìm thấy dòng tiêu đề có cột 'Mã SV' hoặc 'Email'")

    data_rows = rows[header_idx + 1:]
    if len(data_rows) > MAX_IMPORT_ROWS:
        raise HTTPException(status_code=400, detail=f"Tối đa {MAX_IMPORT_ROWS} sinh viên mỗi lần import")

    out = []
    for offset, row in enumerate(data_rows):
        def get(field: str) -> str:
            idx = cols.get(field)
            return row[idx].strip() if idx is not None and idx < len(row) else ""
        record = {"code": get("code"), "name": get("name"), "email": get("email").lower()}
        if any(record.values()):
            out.append((header_idx + offset + 2, record))  # số dòng như trong Excel (1-based)
    return out


def import_students(course_id: str, filename: str, data: bytes) -> StudentImportResult:
    """Ghi danh các sinh viên trong file vào lớp; không tạo tài khoản mới."""
    from app.services.enrollment_service import enrollment_service

    result = StudentImportResult()
    for line_no, row in parse_rows(filename, data):
        code, email = row["code"], row["email"]
        label = code or email
        user = (crud_user.get_by_user_code(code) if code else None) or (crud_user.get_by_email(email) if email else None)
        if not user:
            result.errors.append(f"Dòng {line_no}: {label} chưa có tài khoản trong hệ thống")
            continue
        if user.role != UserRole.STUDENT:
            result.errors.append(f"Dòng {line_no}: {label} không phải tài khoản sinh viên")
            continue
        if crud_enrollment.is_enrolled(str(user.id), course_id):
            result.already_enrolled += 1
            continue
        try:
            enrollment_service.enroll(EnrollmentCreate(user_id=str(user.id), course_id=course_id))
            result.enrolled += 1
        except HTTPException as exc:
            result.errors.append(f"Dòng {line_no}: {label} — {exc.detail}")
    return result
