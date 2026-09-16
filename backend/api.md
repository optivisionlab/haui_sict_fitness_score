# Haui Sport Fitness Score — API Specification

> **Frontend:** `https://haui-fe-fitness-score.vercel.app/`  
> **Backend stack:** FastAPI + PyMongo + Pydantic v2  
> **Database:** MongoDB  
> **Purpose:** REST API contract required by the Haui Sport Fitness Score frontend.

## 1. API Conventions

### Base URL

```text
{API_BASE_URL}/api/v1
```

Example:

```text
GET {API_BASE_URL}/api/v1/courses
```

### Headers

For JSON requests:

```http
Content-Type: application/json
Authorization: Bearer <access_token>
```

For video upload:

```http
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

### Common response format

Successful single-resource response:

```json
{
  "data": {},
  "message": "Success"
}
```

Successful list response:

```json
{
  "data": [],
  "pagination": {
    "page": 1,
    "pageSize": 20,
    "total": 100,
    "totalPages": 5
  }
}
```

Error response:

```json
{
  "detail": "Resource not found"
}
```

### ID format

MongoDB `_id` values are exposed to the frontend as strings:

```json
{
  "id": "64c1d2e3f4a5b6789012cdef"
}
```

---

# 2. API Overview

| Domain | Method | Endpoint | Purpose |
|---|---|---|---|
| Auth | POST | `/auth/login` | Authenticate a user |
| Auth | GET | `/auth/me` | Get current user |
| Auth | POST | `/auth/logout` | End current session |
| Users | GET | `/users/{userId}` | Get user information |
| Dashboard | GET | `/dashboard/student` | Student dashboard data |
| Dashboard | GET | `/dashboard/teacher` | Teacher dashboard data |
| Sports | GET | `/sports` | List sports |
| Sports | GET | `/sports/{sportId}` | Get sport configuration |
| Sports | POST | `/sports` | Create a sport |
| Sports | PATCH | `/sports/{sportId}` | Update a sport |
| Courses | GET | `/courses` | List courses |
| Courses | GET | `/courses/{courseId}` | Get course details |
| Courses | POST | `/courses` | Create a course |
| Courses | PATCH | `/courses/{courseId}` | Update a course |
| Courses | DELETE | `/courses/{courseId}` | Delete a course |
| Tasks | GET | `/courses/{courseId}/tasks` | List course tasks |
| Tasks | GET | `/tasks/{taskId}` | Get task details |
| Tasks | POST | `/courses/{courseId}/tasks` | Create a task |
| Tasks | PATCH | `/tasks/{taskId}` | Update a task |
| Tasks | DELETE | `/tasks/{taskId}` | Delete a task |
| Enrollment | GET | `/courses/{courseId}/students` | List enrolled students |
| Enrollment | POST | `/courses/{courseId}/enrollments` | Enroll a student |
| Enrollment | DELETE | `/courses/{courseId}/enrollments/{userId}` | Remove a student |
| Enrollment | GET | `/students/{userId}/courses` | Student's courses |
| Enrollment | GET | `/courses/{courseId}/progress/{userId}` | Student course progress |
| Video | POST | `/tasks/{taskId}/video-results` | Submit video assessment |
| Video | GET | `/video-results/{resultId}` | Get video result |
| Video | GET | `/tasks/{taskId}/video-results` | List task video results |
| Video | GET | `/students/{userId}/video-results` | List student's video results |
| Video | POST | `/video-results/{resultId}/retry` | Retry AI processing |
| Live | POST | `/tasks/{taskId}/live-results` | Create live assessment |
| Live | PATCH | `/live-results/{resultId}` | Update live assessment |
| Live | GET | `/live-results/{resultId}` | Get live result |
| Cameras | GET | `/cameras` | List cameras |
| Cameras | GET | `/cameras/{cameraId}` | Get camera |
| Cameras | POST | `/cameras` | Create camera |
| Cameras | PATCH | `/cameras/{cameraId}` | Update camera |
| Cameras | DELETE | `/cameras/{cameraId}` | Delete camera |
| Grading | PATCH | `/video-results/{resultId}/grade` | Teacher grades video result |
| Grading | PATCH | `/live-results/{resultId}/grade` | Teacher finalizes live result |

---

# 3. Authentication APIs

The database schema references `users._id`, although `users` is outside the eight collections defined in the supplied MongoDB schema. Therefore authentication/user-management APIs are treated as an external user/auth module.

## 3.1 Login

### `POST /api/v1/auth/login`

**Purpose:** Authenticate a student, teacher, or administrator and return an access token.

### Input

```json
{
  "username": "student01",
  "password": "password"
}
```

### Output

```json
{
  "data": {
    "accessToken": "jwt-token",
    "tokenType": "bearer",
    "user": {
      "id": "user-001",
      "name": "Nguyen Van A",
      "email": "student01@haui.edu.vn",
      "role": "student"
    }
  },
  "message": "Login successful"
}
```

---

## 3.2 Current User

### `GET /api/v1/auth/me`

**Purpose:** Return the currently authenticated user's basic information.

### Input

No body.

### Output

```json
{
  "data": {
    "id": "user-001",
    "name": "Nguyen Van A",
    "email": "student01@haui.edu.vn",
    "role": "student"
  }
}
```

---

## 3.3 Logout

### `POST /api/v1/auth/logout`

**Purpose:** Invalidate the current session/token when the authentication implementation requires server-side session management.

### Input

No body.

### Output

```json
{
  "message": "Logout successful"
}
```

---

# 4. User APIs

## 4.1 Get User

### `GET /api/v1/users/{userId}`

**Purpose:** Get profile information required by course, dashboard, enrollment, and result pages.

### Input

Path parameter:

```text
userId: string
```

### Output

```json
{
  "data": {
    "id": "user-001",
    "name": "Nguyen Van A",
    "email": "student01@haui.edu.vn",
    "role": "student",
    "studentCode": "2022600001"
  }
}
```

---

# 5. Dashboard APIs

Dashboard APIs aggregate data from multiple MongoDB collections so the frontend does not need to perform many independent requests.

## 5.1 Student Dashboard

### `GET /api/v1/dashboard/student`

**Purpose:** Return the data required for the student home/dashboard page.

### Query parameters

```text
courseId: optional
```

### Output

```json
{
  "data": {
    "student": {
      "id": "user-001",
      "name": "Nguyen Van A"
    },
    "courses": [
      {
        "id": "course-001",
        "name": "Physical Education 1",
        "progressPercent": 72.5,
        "examDate": "2026-10-20T00:00:00Z"
      }
    ],
    "recentResults": [
      {
        "id": "result-001",
        "taskId": "task-001",
        "sportId": "sport-001",
        "sportName": "Badminton",
        "score": 8.5,
        "mode": "video",
        "submittedAt": "2026-09-15T08:00:00Z"
      }
    ],
    "summary": {
      "courseCount": 2,
      "completedTaskCount": 8,
      "averageScore": 8.1
    }
  }
}
```

---

## 5.2 Teacher Dashboard

### `GET /api/v1/dashboard/teacher`

**Purpose:** Return course, student, task, and assessment statistics for a teacher.

### Query parameters

```text
courseId: optional
```

### Output

```json
{
  "data": {
    "summary": {
      "courseCount": 3,
      "studentCount": 120,
      "pendingVideoResults": 8,
      "completedAssessments": 245
    },
    "courses": [
      {
        "id": "course-001",
        "name": "Physical Education 1",
        "studentTotal": 40,
        "taskCount": 6
      }
    ]
  }
}
```

---

# 6. Sport APIs

The `sports` collection stores reusable sport definitions and scoring configuration. Sport does **not** contain `mode`; assessment mode belongs to Task.

## 6.1 List Sports

### `GET /api/v1/sports`

**Purpose:** Display available sports when creating/viewing Tasks.

### Query parameters

```text
page: integer = 1
pageSize: integer = 20
search: optional string
```

### Output

```json
{
  "data": [
    {
      "id": "sport-001",
      "code": "badminton",
      "name": "Badminton",
      "scoringConfig": {
        "metricsFields": [
          "hitCount",
          "missCount",
          "postureScore"
        ],
        "formula": "0.5 * hitRate + 0.5 * postureScore",
        "thresholds": {
          "excellent": 9,
          "good": 7,
          "pass": 5
        }
      }
    }
  ],
  "pagination": {
    "page": 1,
    "pageSize": 20,
    "total": 1,
    "totalPages": 1
  }
}
```

---

## 6.2 Get Sport

### `GET /api/v1/sports/{sportId}`

**Purpose:** Get one sport and its scoring configuration.

### Output

```json
{
  "data": {
    "id": "sport-001",
    "code": "badminton",
    "name": "Badminton",
    "scoringConfig": {
      "metricsFields": [
        "hitCount",
        "missCount",
        "postureScore"
      ],
      "formula": "0.5 * hitRate + 0.5 * postureScore",
      "thresholds": {
        "excellent": 9,
        "good": 7,
        "pass": 5
      }
    }
  }
}
```

---

## 6.3 Create Sport

### `POST /api/v1/sports`

**Purpose:** Create a reusable sport definition.

### Input

```json
{
  "code": "badminton",
  "name": "Badminton",
  "scoringConfig": {
    "metricsFields": [
      "hitCount",
      "missCount",
      "postureScore"
    ],
    "formula": "0.5 * hitRate + 0.5 * postureScore",
    "thresholds": {
      "excellent": 9,
      "good": 7,
      "pass": 5
    }
  }
}
```

### Output

```json
{
  "data": {
    "id": "sport-001",
    "code": "badminton",
    "name": "Badminton",
    "scoringConfig": {}
  },
  "message": "Sport created successfully"
}
```

---

## 6.4 Update Sport

### `PATCH /api/v1/sports/{sportId}`

**Purpose:** Update sport name or scoring configuration.

### Input

```json
{
  "name": "Badminton",
  "scoringConfig": {
    "metricsFields": [
      "hitCount",
      "missCount",
      "postureScore"
    ],
    "formula": "0.5 * hitRate + 0.5 * postureScore",
    "thresholds": {
      "excellent": 9,
      "good": 7,
      "pass": 5
    }
  }
}
```

### Output

```json
{
  "data": {
    "id": "sport-001",
    "code": "badminton",
    "name": "Badminton",
    "scoringConfig": {}
  },
  "message": "Sport updated successfully"
}
```

---

# 7. Course APIs

The `courses` collection owns class/course information and bounded weekly content.

## 7.1 List Courses

### `GET /api/v1/courses`

**Purpose:** List courses for the student or teacher.

### Query parameters

```text
page: integer = 1
pageSize: integer = 20
teacherId: optional string
studentId: optional string
search: optional string
```

### Output

```json
{
  "data": [
    {
      "id": "course-001",
      "key": "pe-01",
      "name": "Physical Education 1",
      "teacherId": "teacher-001",
      "teacherName": "Tran Van B",
      "startDate": "2026-09-01T00:00:00Z",
      "endDate": "2026-12-30T00:00:00Z",
      "examDate": "2026-12-20T00:00:00Z",
      "code": "PE101",
      "desc": "Physical Education course",
      "studentTotal": 40,
      "weeks": []
    }
  ],
  "pagination": {
    "page": 1,
    "pageSize": 20,
    "total": 1,
    "totalPages": 1
  }
}
```

---

## 7.2 Get Course

### `GET /api/v1/courses/{courseId}`

**Purpose:** Return complete course information, including weekly content and task references.

### Output

```json
{
  "data": {
    "id": "course-001",
    "key": "pe-01",
    "name": "Physical Education 1",
    "teacherId": "teacher-001",
    "teacherName": "Tran Van B",
    "startDate": "2026-09-01T00:00:00Z",
    "endDate": "2026-12-30T00:00:00Z",
    "examDate": "2026-12-20T00:00:00Z",
    "code": "PE101",
    "desc": "Physical Education course",
    "studentTotal": 40,
    "weeks": [
      {
        "week": 1,
        "title": "Introduction",
        "items": [
          {
            "title": "Basic racket exercise",
            "type": "practice",
            "taskId": "task-001"
          }
        ]
      }
    ]
  }
}
```

---

## 7.3 Create Course

### `POST /api/v1/courses`

**Purpose:** Create a new course/class.

### Input

```json
{
  "key": "pe-01",
  "name": "Physical Education 1",
  "teacherId": "teacher-001",
  "teacherName": "Tran Van B",
  "startDate": "2026-09-01T00:00:00Z",
  "endDate": "2026-12-30T00:00:00Z",
  "examDate": "2026-12-20T00:00:00Z",
  "code": "PE101",
  "desc": "Physical Education course",
  "weeks": []
}
```

`studentTotal` should be initialized by the backend and should not be trusted from the client.

### Output

```json
{
  "data": {
    "id": "course-001",
    "name": "Physical Education 1",
    "studentTotal": 0,
    "weeks": []
  },
  "message": "Course created successfully"
}
```

---

## 7.4 Update Course

### `PATCH /api/v1/courses/{courseId}`

**Purpose:** Update course metadata or weekly learning content.

### Input

```json
{
  "name": "Physical Education 1 - Updated",
  "examDate": "2026-12-22T00:00:00Z",
  "desc": "Updated course description",
  "weeks": []
}
```

### Output

```json
{
  "data": {
    "id": "course-001",
    "name": "Physical Education 1 - Updated"
  },
  "message": "Course updated successfully"
}
```

---

## 7.5 Delete Course

### `DELETE /api/v1/courses/{courseId}`

**Purpose:** Remove a course when it is no longer needed.

### Output

```json
{
  "message": "Course deleted successfully"
}
```

The backend should define whether associated Tasks and Enrollments are deleted, archived, or rejected. The database schema itself does not specify a cascade-delete policy.

---

# 8. Task APIs

A Task is the concrete assessment unit:

```text
Task = Sport + Mode + Task-specific configuration
```

The assessment mode is either `video` or `camera`.

## 8.1 List Course Tasks

### `GET /api/v1/courses/{courseId}/tasks`

**Purpose:** List all assessment Tasks belonging to a Course.

### Query parameters

```text
mode: optional "video" | "camera"
sportId: optional string
page: integer = 1
pageSize: integer = 20
```

### Output

```json
{
  "data": [
    {
      "id": "task-001",
      "courseId": "course-001",
      "sportId": "sport-001",
      "sportName": "Badminton",
      "mode": "video",
      "title": "Badminton Basic Stroke",
      "gradingMethod": "ai",
      "timeLimit": 120,
      "openTime": "2026-09-15T00:00:00Z",
      "closeTime": "2026-10-15T00:00:00Z",
      "cameraId": null
    }
  ],
  "pagination": {
    "page": 1,
    "pageSize": 20,
    "total": 1,
    "totalPages": 1
  }
}
```

---

## 8.2 Get Task

### `GET /api/v1/tasks/{taskId}`

**Purpose:** Get a Task together with its Sport and Course display information.

### Output

```json
{
  "data": {
    "id": "task-001",
    "courseId": "course-001",
    "sportId": "sport-001",
    "mode": "video",
    "title": "Badminton Basic Stroke",
    "gradingMethod": "ai",
    "timeLimit": 120,
    "openTime": "2026-09-15T00:00:00Z",
    "closeTime": "2026-10-15T00:00:00Z",
    "cameraId": null,
    "sport": {
      "id": "sport-001",
      "code": "badminton",
      "name": "Badminton"
    }
  }
}
```

---

## 8.3 Create Task

### `POST /api/v1/courses/{courseId}/tasks`

**Purpose:** Create a concrete assessment Task.

### Input — Video Task

```json
{
  "sportId": "sport-001",
  "mode": "video",
  "title": "Badminton Basic Stroke",
  "gradingMethod": "ai",
  "timeLimit": 120,
  "openTime": "2026-09-15T00:00:00Z",
  "closeTime": "2026-10-15T00:00:00Z",
  "cameraId": null
}
```

### Input — Camera Task

```json
{
  "sportId": "sport-001",
  "mode": "camera",
  "title": "Live Badminton Assessment",
  "gradingMethod": "ai",
  "timeLimit": 120,
  "openTime": "2026-09-15T00:00:00Z",
  "closeTime": "2026-10-15T00:00:00Z",
  "cameraId": "camera-001"
}
```

### Output

```json
{
  "data": {
    "id": "task-001",
    "courseId": "course-001",
    "sportId": "sport-001",
    "mode": "video",
    "title": "Badminton Basic Stroke",
    "cameraId": null
  },
  "message": "Task created successfully"
}
```

### Validation

The backend must enforce:

```text
mode = "video"  -> cameraId = null
mode = "camera" -> cameraId is required
```

---

## 8.4 Update Task

### `PATCH /api/v1/tasks/{taskId}`

**Purpose:** Update task configuration.

### Input

```json
{
  "title": "Badminton Advanced Stroke",
  "gradingMethod": "ai",
  "timeLimit": 180,
  "openTime": "2026-09-20T00:00:00Z",
  "closeTime": "2026-10-20T00:00:00Z"
}
```

### Output

```json
{
  "data": {
    "id": "task-001",
    "title": "Badminton Advanced Stroke",
    "timeLimit": 180
  },
  "message": "Task updated successfully"
}
```

---

## 8.5 Delete Task

### `DELETE /api/v1/tasks/{taskId}`

**Purpose:** Delete or deactivate an assessment Task.

### Output

```json
{
  "message": "Task deleted successfully"
}
```

---

# 9. Enrollment APIs

The `enrollments` collection is the authoritative source of course membership. `courses.studentTotal` and `enrollments.taskScores` are caches.

## 9.1 List Course Students

### `GET /api/v1/courses/{courseId}/students`

**Purpose:** Display all students enrolled in a Course.

### Query parameters

```text
page: integer = 1
pageSize: integer = 20
search: optional string
status: optional "active" | "done"
```

### Output

```json
{
  "data": [
    {
      "userId": "user-001",
      "name": "Nguyen Van A",
      "studentCode": "2022600001",
      "status": "active",
      "progressPercent": 72.5
    }
  ],
  "pagination": {
    "page": 1,
    "pageSize": 20,
    "total": 40,
    "totalPages": 2
  }
}
```

---

## 9.2 Enroll Student

### `POST /api/v1/courses/{courseId}/enrollments`

**Purpose:** Add a student to a Course.

### Input

```json
{
  "userId": "user-001"
}
```

### Output

```json
{
  "data": {
    "id": "enrollment-001",
    "userId": "user-001",
    "courseId": "course-001",
    "status": "active",
    "progressPercent": 0,
    "completedTaskIds": [],
    "taskScores": {}
  },
  "message": "Student enrolled successfully"
}
```

The backend should atomically increment `courses.studentTotal`.

---

## 9.3 Remove Student

### `DELETE /api/v1/courses/{courseId}/enrollments/{userId}`

**Purpose:** Remove a student from a Course.

### Output

```json
{
  "message": "Student removed successfully"
}
```

The backend should atomically decrement `courses.studentTotal`.

---

## 9.4 Student Courses

### `GET /api/v1/students/{userId}/courses`

**Purpose:** List all courses in which a student is enrolled.

### Output

```json
{
  "data": [
    {
      "courseId": "course-001",
      "courseName": "Physical Education 1",
      "teacherName": "Tran Van B",
      "status": "active",
      "progressPercent": 72.5,
      "examDate": "2026-12-20T00:00:00Z"
    }
  ]
}
```

---

## 9.5 Student Course Progress

### `GET /api/v1/courses/{courseId}/progress/{userId}`

**Purpose:** Return detailed progress and cached task scores for a student.

### Output

```json
{
  "data": {
    "courseId": "course-001",
    "userId": "user-001",
    "progressPercent": 72.5,
    "completedTaskIds": [
      "task-001",
      "task-002"
    ],
    "taskScores": {
      "task-001": 8.5,
      "task-002": 9.0
    }
  }
}
```

`taskScores` is a cache. When score accuracy matters, the frontend should use the Result APIs as the authoritative source.

---

# 10. Video Assessment APIs

A video Task produces records in `video_results`.

## 10.1 Submit Video Assessment

### `POST /api/v1/tasks/{taskId}/video-results`

**Purpose:** Upload a student's video submission and create a pending AI assessment.

### Input

`multipart/form-data`

```text
video: File
attemptNo: integer
```

Optional metadata:

```text
durationSec: integer
```

### Output

```json
{
  "data": {
    "id": "video-result-001",
    "taskId": "task-001",
    "sportId": "sport-001",
    "userId": "user-001",
    "attemptNo": 1,
    "submittedAt": "2026-09-15T10:00:00Z",
    "pending": true,
    "videoUrl": "https://storage.example.com/video-result-001.mp4",
    "durationSec": 45,
    "metrics": {},
    "aiScore": null,
    "aiComment": null,
    "finalScore": null,
    "teacherComment": null
  },
  "message": "Video submitted successfully"
}
```

The backend must verify that:

```text
Task.mode == "video"
```

before creating the result.

---

## 10.2 Get Video Result

### `GET /api/v1/video-results/{resultId}`

**Purpose:** Get the current state and AI/teacher assessment of a video submission.

### Output

```json
{
  "data": {
    "id": "video-result-001",
    "taskId": "task-001",
    "sportId": "sport-001",
    "userId": "user-001",
    "attemptNo": 1,
    "submittedAt": "2026-09-15T10:00:00Z",
    "pending": false,
    "videoUrl": "https://storage.example.com/video-result-001.mp4",
    "durationSec": 45,
    "metrics": {
      "hitCount": 18,
      "missCount": 2,
      "postureScore": 8.7
    },
    "aiScore": 8.5,
    "aiComment": "Good consistency and posture.",
    "finalScore": 8.5,
    "teacherComment": null,
    "gradedBy": null,
    "gradedAt": null
  }
}
```

---

## 10.3 List Video Results for a Task

### `GET /api/v1/tasks/{taskId}/video-results`

**Purpose:** Allow teachers to see all student submissions for a video Task.

### Query parameters

```text
userId: optional string
pending: optional boolean
page: integer = 1
pageSize: integer = 20
```

### Output

```json
{
  "data": [
    {
      "id": "video-result-001",
      "userId": "user-001",
      "attemptNo": 1,
      "pending": false,
      "aiScore": 8.5,
      "finalScore": 8.5,
      "submittedAt": "2026-09-15T10:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "pageSize": 20,
    "total": 40,
    "totalPages": 2
  }
}
```

---

## 10.4 List Student Video Results

### `GET /api/v1/students/{userId}/video-results`

**Purpose:** Display a student's video assessment history.

### Query parameters

```text
courseId: optional string
taskId: optional string
sportId: optional string
page: integer = 1
pageSize: integer = 20
```

### Output

```json
{
  "data": [
    {
      "id": "video-result-001",
      "taskId": "task-001",
      "sportId": "sport-001",
      "sportName": "Badminton",
      "taskTitle": "Badminton Basic Stroke",
      "attemptNo": 1,
      "pending": false,
      "aiScore": 8.5,
      "finalScore": 8.5,
      "submittedAt": "2026-09-15T10:00:00Z"
    }
  ]
}
```

---

## 10.5 Retry Video AI Processing

### `POST /api/v1/video-results/{resultId}/retry`

**Purpose:** Requeue a failed or incomplete AI video-processing job.

### Input

No body.

### Output

```json
{
  "data": {
    "id": "video-result-001",
    "pending": true
  },
  "message": "Video processing has been queued again"
}
```

---

# 11. Video Grading APIs

## 11.1 Teacher Grade Video Result

### `PATCH /api/v1/video-results/{resultId}/grade`

**Purpose:** Allow a teacher to override/confirm the AI result and provide feedback.

### Input

```json
{
  "finalScore": 9.0,
  "teacherComment": "Good performance. Improve the follow-through."
}
```

### Output

```json
{
  "data": {
    "id": "video-result-001",
    "aiScore": 8.5,
    "finalScore": 9.0,
    "teacherComment": "Good performance. Improve the follow-through.",
    "gradedBy": "teacher-001",
    "gradedAt": "2026-09-15T11:00:00Z"
  },
  "message": "Result graded successfully"
}
```

After final grading, the backend may update:

```text
enrollments.taskScores[taskId]
enrollments.completedTaskIds
enrollments.progressPercent
```

These are cache/progress fields, not the authoritative result.

---

# 12. Live Camera Assessment APIs

A camera Task produces records in `live_results`.

## 12.1 Start Live Assessment

### `POST /api/v1/tasks/{taskId}/live-results`

**Purpose:** Start a real-time assessment for a student.

### Input

```json
{
  "userId": "user-001"
}
```

### Output

```json
{
  "data": {
    "id": "live-result-001",
    "taskId": "task-002",
    "sportId": "sport-001",
    "userId": "user-001",
    "cameraId": "camera-001",
    "startedAt": "2026-09-15T14:00:00Z",
    "completedAt": null,
    "metrics": {},
    "score": null
  },
  "message": "Live assessment started"
}
```

The backend must verify:

```text
Task.mode == "camera"
Task.cameraId == requested camera
```

---

## 12.2 Update Live Assessment

### `PATCH /api/v1/live-results/{resultId}`

**Purpose:** Update real-time metrics while the assessment is running or complete the assessment.

### Input

```json
{
  "completedAt": "2026-09-15T14:05:00Z",
  "metrics": {
    "hitCount": 25,
    "missCount": 3,
    "postureScore": 8.8
  },
  "score": 8.6
}
```

### Output

```json
{
  "data": {
    "id": "live-result-001",
    "completedAt": "2026-09-15T14:05:00Z",
    "metrics": {
      "hitCount": 25,
      "missCount": 3,
      "postureScore": 8.8
    },
    "score": 8.6
  },
  "message": "Live assessment updated"
}
```

---

## 12.3 Get Live Result

### `GET /api/v1/live-results/{resultId}`

**Purpose:** Display the final or current live assessment.

### Output

```json
{
  "data": {
    "id": "live-result-001",
    "taskId": "task-002",
    "sportId": "sport-001",
    "userId": "user-001",
    "cameraId": "camera-001",
    "startedAt": "2026-09-15T14:00:00Z",
    "completedAt": "2026-09-15T14:05:00Z",
    "metrics": {
      "hitCount": 25,
      "missCount": 3,
      "postureScore": 8.8
    },
    "score": 8.6
  }
}
```

---

## 12.4 Teacher Finalize Live Result

### `PATCH /api/v1/live-results/{resultId}/grade`

**Purpose:** Allow a teacher to confirm or override the live assessment score.

### Input

```json
{
  "score": 9.0,
  "teacherComment": "Good performance."
}
```

### Output

```json
{
  "data": {
    "id": "live-result-001",
    "score": 9.0,
    "teacherComment": "Good performance."
  },
  "message": "Live result finalized successfully"
}
```

> If teacher comments or `gradedBy` fields are required for live results, the MongoDB schema should be extended because the current `live_results` schema only defines `score`.

---

# 13. Camera APIs

The `cameras` collection stores physical camera devices.

## 13.1 List Cameras

### `GET /api/v1/cameras`

**Purpose:** Display available cameras when creating camera-based Tasks and monitor camera status.

### Query parameters

```text
status: optional "online" | "offline" | "error"
page: integer = 1
pageSize: integer = 20
```

### Output

```json
{
  "data": [
    {
      "id": "camera-001",
      "name": "Gym Camera 01",
      "location": "Gymnasium A",
      "streamUrl": "rtsp://camera.example/stream",
      "status": "online"
    }
  ],
  "pagination": {
    "page": 1,
    "pageSize": 20,
    "total": 1,
    "totalPages": 1
  }
}
```

---

## 13.2 Get Camera

### `GET /api/v1/cameras/{cameraId}`

**Purpose:** Get camera configuration and current status.

### Output

```json
{
  "data": {
    "id": "camera-001",
    "name": "Gym Camera 01",
    "location": "Gymnasium A",
    "streamUrl": "rtsp://camera.example/stream",
    "status": "online"
  }
}
```

---

## 13.3 Create Camera

### `POST /api/v1/cameras`

**Purpose:** Register a physical camera device.

### Input

```json
{
  "name": "Gym Camera 01",
  "location": "Gymnasium A",
  "streamUrl": "rtsp://camera.example/stream",
  "status": "offline"
}
```

### Output

```json
{
  "data": {
    "id": "camera-001",
    "name": "Gym Camera 01",
    "location": "Gymnasium A",
    "streamUrl": "rtsp://camera.example/stream",
    "status": "offline"
  },
  "message": "Camera created successfully"
}
```

---

## 13.4 Update Camera

### `PATCH /api/v1/cameras/{cameraId}`

**Purpose:** Update camera metadata, stream URL, or status.

### Input

```json
{
  "name": "Gym Camera 01",
  "location": "Gymnasium A",
  "streamUrl": "rtsp://camera.example/new-stream",
  "status": "online"
}
```

### Output

```json
{
  "data": {
    "id": "camera-001",
    "status": "online"
  },
  "message": "Camera updated successfully"
}
```

---

## 13.5 Delete Camera

### `DELETE /api/v1/cameras/{cameraId}`

**Purpose:** Remove a camera that is no longer available.

### Output

```json
{
  "message": "Camera deleted successfully"
}
```

The backend should reject deletion if the camera is still referenced by an active camera Task, or define an explicit deactivation policy.

---

# 14. Recommended Frontend Data Flows

## 14.1 Student Course Page

```text
GET /courses
        ↓
GET /courses/{courseId}
        ↓
GET /courses/{courseId}/tasks
        ↓
GET /courses/{courseId}/progress/{userId}
```

The frontend can display:

- Course name
- Teacher
- Course dates
- Exam date
- Weekly content
- Tasks
- Task completion
- Cached scores

---

## 14.2 Student Video Assessment

```text
GET /tasks/{taskId}
        ↓
POST /tasks/{taskId}/video-results
        ↓
GET /video-results/{resultId}
        ↓
poll until pending=false
        ↓
display AI score + metrics + feedback
```

Example lifecycle:

```text
POST video
     ↓
pending = true
     ↓
AI processing
     ↓
pending = false
     ↓
aiScore / aiComment available
```

---

## 14.3 Student Camera Assessment

```text
GET /tasks/{taskId}
        ↓
GET /cameras/{cameraId}
        ↓
POST /tasks/{taskId}/live-results
        ↓
real-time assessment
        ↓
PATCH /live-results/{resultId}
        ↓
GET /live-results/{resultId}
```

---

## 14.4 Teacher Result Management

```text
GET /courses/{courseId}/students
        ↓
GET /courses/{courseId}/tasks
        ↓
GET /tasks/{taskId}/video-results
        ↓
PATCH /video-results/{resultId}/grade
```

For camera Tasks:

```text
GET /tasks/{taskId}
        ↓
GET /live-results/{resultId}
        ↓
PATCH /live-results/{resultId}/grade
```

---

# 15. API Validation Rules

The backend must enforce the following database/domain rules.

### Task rules

```text
Task.mode ∈ {"video", "camera"}

Task.mode == "video"
    => Task.cameraId == null

Task.mode == "camera"
    => Task.cameraId != null
```

### Result rules

```text
video_results
    => Task.mode == "video"

live_results
    => Task.mode == "camera"
```

### Sport consistency

```text
video_results.sportId == Task.sportId
live_results.sportId == Task.sportId
```

### Camera consistency

```text
live_results.cameraId == Task.cameraId
```

### Score authority

```text
video Task
    -> video_results.aiScore / finalScore

camera Task
    -> live_results.score
```

`enrollments.taskScores` is only a cache.

### Enrollment authority

```text
enrollments
```

is the authoritative source for Course membership.

### Course student count

```text
courses.studentTotal
```

is a counter/cache and should be updated atomically when enrollment changes.

---

# 16. Suggested HTTP Status Codes

| Status | Meaning |
|---|---|
| `200 OK` | Successful GET/PATCH request |
| `201 Created` | Resource successfully created |
| `202 Accepted` | Asynchronous AI processing accepted |
| `204 No Content` | Successful deletion when no body is returned |
| `400 Bad Request` | Invalid request data |
| `401 Unauthorized` | Missing/invalid authentication |
| `403 Forbidden` | Authenticated but not allowed |
| `404 Not Found` | Resource does not exist |
| `409 Conflict` | Duplicate enrollment/resource or invalid state transition |
| `422 Unprocessable Entity` | Pydantic/domain validation error |
| `500 Internal Server Error` | Unexpected backend error |
| `503 Service Unavailable` | AI/camera/storage service unavailable |

For video submission, `202 Accepted` is recommended when the video has been stored successfully but AI inference is still running.

---

# 17. Recommended Backend Router Structure

A FastAPI implementation can be organized as:

```text
app/
├── api/
│   └── v1/
│       ├── auth.py
│       ├── users.py
│       ├── dashboard.py
│       ├── sports.py
│       ├── courses.py
│       ├── tasks.py
│       ├── enrollments.py
│       ├── video_results.py
│       ├── live_results.py
│       └── cameras.py
│
├── models/
│   ├── sport.py
│   ├── course.py
│   ├── task.py
│   ├── enrollment.py
│   ├── video_result.py
│   ├── live_result.py
│   └── camera.py
│
├── schemas/
│   ├── sport.py
│   ├── course.py
│   ├── task.py
│   ├── enrollment.py
│   ├── video_result.py
│   ├── live_result.py
│   └── camera.py
│
└── services/
    ├── scoring.py
    ├── video_processing.py
    └── enrollment.py
```

---

# 18. Minimum API Set for the Frontend

If the first backend version only needs to make the core student/teacher frontend functional, implement these APIs first:

```text
POST   /auth/login
GET    /auth/me

GET    /dashboard/student
GET    /dashboard/teacher

GET    /sports
GET    /sports/{sportId}

GET    /courses
GET    /courses/{courseId}

GET    /courses/{courseId}/tasks
GET    /tasks/{taskId}

GET    /students/{userId}/courses
GET    /courses/{courseId}/progress/{userId}

POST   /tasks/{taskId}/video-results
GET    /video-results/{resultId}
GET    /students/{userId}/video-results

POST   /tasks/{taskId}/live-results
PATCH  /live-results/{resultId}
GET    /live-results/{resultId}

GET    /cameras
GET    /cameras/{cameraId}

GET    /courses/{courseId}/students
```

Teacher/admin CRUD APIs can then be implemented:

```text
POST   /sports
PATCH  /sports/{sportId}

POST   /courses
PATCH  /courses/{courseId}
DELETE /courses/{courseId}

POST   /courses/{courseId}/tasks
PATCH  /tasks/{taskId}
DELETE /tasks/{taskId}

POST   /courses/{courseId}/enrollments
DELETE /courses/{courseId}/enrollments/{userId}

PATCH  /video-results/{resultId}/grade
PATCH  /live-results/{resultId}/grade

POST   /cameras
PATCH  /cameras/{cameraId}
DELETE /cameras/{cameraId}
```

---

# 19. Important Implementation Notes

1. **Do not put `mode` in the Sport API.** `mode` belongs to Task.
2. **Do not treat `enrollments.taskScores` as the authoritative score.** Always use `video_results` or `live_results` when exact result data is required.
3. **Do not treat `courses.studentTotal` as the authoritative enrollment count.** The authoritative relationship is stored in `enrollments`.
4. **Video and camera Tasks must produce different Result types.**
5. **A video Task must not reference a camera.**
6. **A camera Task must reference a valid camera.**
7. **`sportId` in both Result collections is denormalized and must remain consistent with `Task.sportId`.**
8. **AI video processing should be asynchronous.** The frontend should initially receive `pending: true` and later retrieve the processed result.
9. **The backend should perform authorization checks based on role.** For example, students should not be able to modify course Tasks or teacher grades.
10. **The `users` collection is not part of the supplied eight-collection MongoDB schema.** Authentication and user APIs therefore need to be implemented against the existing user/authentication service or an additional user collection.

---

# 20. MongoDB-to-API Mapping

| MongoDB Collection | Main API Resource |
|---|---|
| `courses` | `/courses` |
| `sports` | `/sports` |
| `tasks` | `/tasks` and `/courses/{courseId}/tasks` |
| `video_results` | `/video-results` and `/tasks/{taskId}/video-results` |
| `live_results` | `/live-results` and `/tasks/{taskId}/live-results` |
| `enrollments` | `/courses/{courseId}/enrollments`, `/students/{userId}/courses` |
| `cameras` | `/cameras` |
| `users` | `/users`, `/auth` — external to the supplied eight-collection schema |

The core relationship is:

```text
User
  │
  ├── Enrollment ──> Course
  │                     │
  │                     └── Task
  │                           │
  │                           ├── Sport
  │                           │
  │                           ├── mode=video
  │                           │      └── VideoResult
  │                           │
  │                           └── mode=camera
  │                                  └── LiveResult
  │
  └── Results
```

This API structure follows the supplied MongoDB domain model: `Task` defines the assessment, `Sport` defines the sport/scoring configuration, Result collections define actual assessment outcomes, and Enrollment defines course membership.
