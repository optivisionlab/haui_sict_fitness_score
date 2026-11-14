"""Comprehensive script to check current MongoDB data state and relations."""
import sys
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.database import get_db

db = get_db()

print("=" * 70)
print("=== MONGODB DATABASE INSPECTION ===")
print("=" * 70)

collections = sorted(db.list_collection_names())
print(f"Collections found ({len(collections)}): {', '.join(collections)}\n")

for coll_name in collections:
    count = db[coll_name].count_documents({})
    print(f"  - {coll_name:15}: {count} documents")

print("\n" + "=" * 70)
print("=== USERS ===")
user_ids = set()
users_by_role = {}
for u in db.users.find():
    uid = str(u['_id'])
    user_ids.add(uid)
    role = u.get('role', 'unknown')
    users_by_role[role] = users_by_role.get(role, 0) + 1
    print(f"  _id={uid} | {u.get('name','')} | role={role} | email={u.get('email','')}")
print(f"Summary: {users_by_role}")

print("\n=== COURSES ===")
course_ids = set()
for c in db.courses.find():
    cid = str(c['_id'])
    course_ids.add(cid)
    teacher_id = str(c.get('teacher_id') or c.get('teacherId') or '')
    teacher_name = c.get('teacher_name') or c.get('teacherName') or ''
    print(f"  _id={cid} | {c.get('name','')} | code={c.get('code','')} | teacher_id={teacher_id} ({teacher_name})")

print("\n=== SPORTS ===")
sport_ids = set()
for s in db.sports.find():
    sid = str(s['_id'])
    sport_ids.add(sid)
    code = s.get('code', '')
    name = s.get('name', '')
    print(f"  _id={sid} | code={code:12} | name={name}")

print("\n=== TASKS ===")
task_ids = set()
for t in db.tasks.find():
    tid = str(t['_id'])
    task_ids.add(tid)
    cid = str(t.get('course_id') or t.get('courseId') or '')
    sid = str(t.get('sport_id') or t.get('sportId') or '')
    print(f"  _id={tid} | title={t.get('title','')} | course_id={cid} | sport_id={sid}")

print("\n=== ENROLLMENTS (Sample up to 10) ===")
enrollment_count = db.enrollments.count_documents({})
for e in db.enrollments.find().limit(10):
    uid = str(e.get('user_id') or e.get('userId') or '')
    cid = str(e.get('course_id') or e.get('courseId') or '')
    cname = e.get('course_name') or e.get('courseName') or ''
    sname = e.get('student_name') or e.get('studentName') or ''
    tname = c.get('teacher_name') or c.get('teacherName') or ''
    print(f"  _id={e['_id']} | student={sname} (userId={uid}) | course={cname} (courseId={cid}) | status={e.get('status','')}")
if enrollment_count > 10:
    print(f"  ... and {enrollment_count - 10} more enrollments.")

print("\n" + "=" * 70)
print("=== INTEGRITY & RELATIONSHIP CHECKS ===")
print("=" * 70)

# Check courses teacher_id
print("\n[Courses -> Teachers (Users)]")
for c in db.courses.find():
    tid = str(c.get('teacher_id') or c.get('teacherId') or '')
    match = tid in user_ids
    print(f"  Course '{c.get('name','')}' -> teacher_id='{tid}' valid: {match}")

# Check tasks course_id and sport_id
print("\n[Tasks -> Courses & Sports]")
for t in db.tasks.find():
    cid = str(t.get('course_id') or t.get('courseId') or '')
    sid = str(t.get('sport_id') or t.get('sportId') or '')
    c_match = cid in course_ids
    s_match = sid in sport_ids if sid else "N/A"
    print(f"  Task '{t.get('title','')}' -> course valid: {c_match}, sport valid: {s_match}")

# Check enrollments user_id and course_id
print("\n[Enrollments -> Users & Courses]")
invalid_enrollment_users = 0
invalid_enrollment_courses = 0
for e in db.enrollments.find():
    uid = str(e.get('user_id') or e.get('userId') or '')
    cid = str(e.get('course_id') or e.get('courseId') or '')
    if uid not in user_ids:
        invalid_enrollment_users += 1
    if cid not in course_ids:
        invalid_enrollment_courses += 1

print(f"  Total Enrollments checked: {enrollment_count}")
print(f"  Invalid User IDs: {invalid_enrollment_users}")
print(f"  Invalid Course IDs: {invalid_enrollment_courses}")
if invalid_enrollment_users == 0 and invalid_enrollment_courses == 0:
    print("  => Tất cả liên kết trong Enrollments đều hợp lệ và toàn vẹn!")

print("\n" + "=" * 70)

