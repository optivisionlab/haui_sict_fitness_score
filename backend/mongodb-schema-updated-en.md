# MongoDB Schema — AI Physical Education Scoring System

> **Updated:** 2026-09-15  
> **Collections:** 8  
> **Stack:** FastAPI + pymongo (raw driver) + Pydantic v2

## 1. Core Design

The system is an LMS with AI-based physical education assessment. It supports two assessment modes:

| Mode | Description | Result collection |
|---|---|---|
| `video` | Student submits a video; AI processes it asynchronously. | `video_results` |
| `camera` | Student is assessed through a live camera stream. | `live_results` |

### Core domain rule

> **`Task = Sport + Mode`**

This means:

- **Sport** defines *what sport it is* and how its scoring is configured.
- **Task** defines *what assessment is being performed* and *how that task is assessed*.
- The assessment `mode` belongs to **Task**, not Sport.
- A single Sport may therefore have multiple Tasks using different modes.

For example, the same `badminton` Sport can have one video-based Task and another camera-based Task.

---

## 2. Responsibilities of the Main Entities

### 2.1 Sport

`Sport` is the reusable catalog/configuration of a physical education sport.

**Responsibilities:**

- Identify the sport (`code`, `name`).
- Define scoring configuration.
- Define the metrics that AI results may expose.
- Define scoring formulas and thresholds where applicable.
- **Do not define the assessment mode.**

A Sport must not contain `mode`.

```text
Sport
 ├── code
 ├── name
 └── scoringConfig
      ├── metricsFields
      ├── formula
      └── thresholds
```

### 2.2 Task

`Task` represents one concrete exercise, test, or assessment inside a Course.

**Responsibilities:**

- Connect a Course to a Sport.
- Define the assessment mode: `video` or `camera`.
- Define task-specific title, grading method, time limit, and availability.
- Reference a camera only when the Task uses camera mode.

The key relationship is:

```text
Task = Sport + Mode + Task-specific configuration
```

### 2.3 Result

A Result records the outcome of one student's execution/submission of a Task.

There are two physical result collections because their lifecycles differ:

- `video_results` for `Task.mode = "video"`.
- `live_results` for `Task.mode = "camera"`.

Both result types reference:

```text
Task + Sport + User
```

`Sport` is intentionally duplicated in Result as a **denormalized field**. The canonical relationship is still obtained through `taskId → Task → sportId`.

### 2.4 Enrollment

`Enrollment` is the many-to-many bridge between a User and a Course.

**Responsibilities:**

- Record that a student belongs to a Course.
- Track course-level progress.
- Track completed Tasks.
- Provide fast access to cached Task scores.

`taskScores` is **not the source of truth for scores**.

The authoritative score comes from the relevant Result collection.

### 2.5 Course

`Course` represents a concrete course/class offering.

**Responsibilities:**

- Identify the course and teacher.
- Define course dates and exam date.
- Contain bounded weekly learning content.
- Reference Tasks through `weeks[].items[].taskId`.
- Expose a fast student counter through `studentTotal`.

`studentTotal` is a **counter/cache**, not the authoritative enrollment count.

---

# 3. Collection: `courses`

## Responsibilities

`courses` owns course/class information and its bounded weekly structure.

### Fields

| Field | MongoDB | Type | Required | Responsibility |
|---|---|---|---|---|
| `id` | `_id` | ObjectId | Yes | Primary key |
| `key` | `key` | string | No | URL/key identifier |
| `name` | `name` | string | Yes | Course name |
| `teacherId` | `teacherId` | string | Yes | Reference to `users._id` |
| `teacherName` | `teacherName` | string | Yes | Denormalized teacher name |
| `startDate` | `startDate` | Date | No | Course start |
| `endDate` | `endDate` | Date | No | Course end |
| `examDate` | `examDate` | Date | No | Exam date |
| `code` | `code` | string | No | Course code |
| `desc` | `desc` | string | No | Description |
| `studentTotal` | `studentTotal` | int | Yes | **Counter/cache** of enrolled students |
| `weeks` | `weeks` | array | Yes | Bounded weekly content |

### `studentTotal` cache rule

- The authoritative student membership is stored in `enrollments`.
- `studentTotal` exists for fast display/querying.
- Enrollment creation/deletion should update it using `$inc`.
- If the cache becomes inconsistent, it can be rebuilt from `enrollments`.

### `weeks[].items`

Each practice item may reference a Task:

```json
{
  "title": "Basic racket exercise",
  "type": "practice",
  "taskId": "64c1d2e3f4a5b6789012cdef"
}
```

---

# 4. Collection: `sports`

## Responsibilities

`Sports` is the reusable sport catalog and scoring configuration.

### Fields

| Field | MongoDB | Type | Required | Responsibility |
|---|---|---|---|---|
| `id` | `_id` | ObjectId | Yes | Primary key |
| `code` | `code` | string | Yes | Unique sport code |
| `name` | `name` | string | Yes | Display name |
| `scoringConfig` | `scoringConfig` | object | Yes | Sport scoring configuration |

### `ScoringConfig`

| Field | Type | Responsibility |
|---|---|---|
| `metricsFields` | array[string] | Names of AI metrics returned for this sport |
| `formula` | string/null | Suggested scoring formula |
| `thresholds` | object | Scoring thresholds |

### Important change

**Removed:**

```json
"mode": "video"
```

or

```json
"mode": "camera"
```

from Sport.

A Sport describes the sport itself. It does not decide whether an individual assessment uses video or camera.

---

# 5. Collection: `tasks`

## Responsibilities

A Task is the concrete assessment unit connecting:

```text
Course → Task → Sport → Result
```

### Fields

| Field | MongoDB | Type | Required | Responsibility |
|---|---|---|---|---|
| `id` | `_id` | ObjectId | Yes | Primary key |
| `courseId` | `courseId` | string | Yes | Reference to `courses._id` |
| `sportId` | `sportId` | string | Yes | Reference to `sports._id` |
| `mode` | `mode` | enum | Yes | `"video"` or `"camera"` |
| `title` | `title` | string | Yes | Task title |
| `gradingMethod` | `gradingMethod` | string | No | Task-specific grading method |
| `timeLimit` | `timeLimit` | int/null | No | Time limit in seconds |
| `openTime` | `openTime` | Date/null | No | Opening time |
| `closeTime` | `closeTime` | Date/null | No | Closing/deadline time |
| `cameraId` | `cameraId` | string/null | Conditional | Camera reference for camera mode |

## Mode/camera rules

### Video Task

```json
{
  "sportId": "sport-id",
  "mode": "video",
  "cameraId": null
}
```

A video Task produces records in `video_results`.

### Camera Task

```json
{
  "sportId": "sport-id",
  "mode": "camera",
  "cameraId": "camera-id"
}
```

A camera Task produces records in `live_results`.

### Invariants

1. `mode` must be either `"video"` or `"camera"`.
2. `mode == "video"` ⇒ `cameraId == null`.
3. `mode == "camera"` ⇒ `cameraId` is required and must reference an existing camera.
4. `video_results` may only be created for Tasks with `mode="video"`.
5. `live_results` may only be created for Tasks with `mode="camera"`.

---

# 6. Collection: `video_results`

## Responsibilities

Stores a student's video submission and the resulting AI/teacher assessment.

### Fields

| Field | MongoDB | Type | Responsibility |
|---|---|---|---|
| `id` | `_id` | ObjectId | Primary key |
| `taskId` | `taskId` | string | Reference to Task |
| `sportId` | `sportId` | string | **Denormalized from `Task.sportId`** |
| `userId` | `userId` | string | Student reference |
| `attemptNo` | `attemptNo` | int | Submission attempt |
| `submittedAt` | `submittedAt` | Date | Submission time |
| `pending` | `pending` | bool | AI processing state |
| `videoUrl` | `videoUrl` | string/null | Stored video URL |
| `durationSec` | `durationSec` | int/null | Video duration |
| `metrics` | `metrics` | object | Sport-specific AI metrics |
| `aiScore` | `aiScore` | float/null | AI score |
| `aiComment` | `aiComment` | string/null | AI feedback |
| `finalScore` | `finalScore` | float/null | Teacher-overridden/final score |
| `teacherComment` | `teacherComment` | string/null | Teacher feedback |
| `gradedBy` | `gradedBy` | string/null | Teacher reference |
| `gradedAt` | `gradedAt` | Date/null | Teacher grading time |

### Denormalization rule

`video_results.sportId` must equal:

```text
video_results.taskId
        ↓
tasks.sportId
```

It is duplicated only to make frequent result queries faster.

The canonical relationship remains `taskId`.

---

# 7. Collection: `live_results`

## Responsibilities

Stores real-time assessment results for camera-based Tasks.

### Fields

| Field | MongoDB | Type | Responsibility |
|---|---|---|---|
| `id` | `_id` | ObjectId | Primary key |
| `taskId` | `taskId` | string | Reference to Task |
| `sportId` | `sportId` | string | **Denormalized from `Task.sportId`** |
| `userId` | `userId` | string | Student reference |
| `cameraId` | `cameraId` | string | Camera reference |
| `startedAt` | `startedAt` | Date | Assessment start |
| `completedAt` | `completedAt` | Date/null | Assessment completion |
| `metrics` | `metrics` | object | Sport-specific real-time metrics |
| `score` | `score` | float/null | Assessment score |

### Denormalization rule

`live_results.sportId` must equal `tasks.sportId` for the referenced `taskId`.

`live_results.cameraId` should also be consistent with the Task's `cameraId`.

---

# 8. Collection: `enrollments`

## Responsibilities

`enrollments` is the authoritative relationship between a student and a Course.

### Fields

| Field | MongoDB | Type | Responsibility |
|---|---|---|---|
| `id` | `_id` | ObjectId | Primary key |
| `userId` | `userId` | string | Reference to User |
| `courseId` | `courseId` | string | Reference to Course |
| `status` | `status` | enum | `"active"` / `"done"` |
| `progressPercent` | `progressPercent` | float | Cached course progress |
| `courseName` | `courseName` | string | Denormalized course name |
| `teacherName` | `teacherName` | string | Denormalized teacher name |
| `examDate` | `examDate` | Date | Denormalized exam date |
| `completedTaskIds` | `completedTaskIds` | array[string] | Completed Task references |
| `taskScores` | `taskScores` | object | **Cached Task scores** |

## `taskScores` cache rule

`taskScores` is not the source of truth.

The authoritative score is stored in:

```text
Task.mode = video  → video_results
Task.mode = camera → live_results
```

When a result becomes the accepted/final result for a Task, the backend may update:

```json
"taskScores": {
  "task-id": 8.5
}
```

This provides fast progress/result reads without repeatedly querying all Result documents.

If `taskScores` conflicts with Result data:

> **Result data wins. `taskScores` must be rebuilt/updated.**

---

# 9. Collection: `cameras`

## Responsibilities

`cameras` represents physical camera devices.

A camera can be reused by multiple Tasks over time.

### Fields

| Field | MongoDB | Type | Responsibility |
|---|---|---|---|
| `id` | `_id` | ObjectId | Primary key |
| `name` | `name` | string | Camera name |
| `location` | `location` | string/null | Physical location |
| `streamUrl` | `streamUrl` | string | RTSP/HLS stream |
| `status` | `status` | enum | `online` / `offline` / `error` |

---

# 10. Updated Relationship Model

```text
                         ┌──────────────┐
                         │    users     │
                         └──────┬───────┘
                                │
                                │ userId
                                ▼
                       ┌────────────────┐
                       │  enrollments   │
                       │                │
                       │ taskScores     │
                       │   = CACHE      │
                       └───────┬────────┘
                               │
                               │ courseId
                               ▼
                         ┌──────────────┐
                         │   courses    │
                         │              │
                         │ studentTotal │
                         │   = CACHE    │
                         └──────┬───────┘
                                │
                     weeks[].items[].taskId
                                │
                                ▼
                         ┌──────────────┐
                         │    tasks     │
                         │              │
                         │ sportId      │
                         │ mode         │
                         │ cameraId*    │
                         └──────┬───────┘
                                │
                   ┌────────────┴────────────┐
                   │                         │
                   │ sportId                 │ taskId
                   ▼                         ▼
             ┌──────────────┐        ┌──────────────────┐
             │    sports    │        │      Results     │
             │              │        │                  │
             │ sport config │        │ video_results    │
             └──────────────┘        │ live_results     │
                                     └──────────────────┘
                                            │
                                            │ denormalized
                                            │ sportId
                                            ▼
                                      ┌──────────────┐
                                      │    sports    │
                                      └──────────────┘

                         * cameraId only for mode="camera"

                         Task.mode
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
        mode="video"              mode="camera"
              │                         │
              ▼                         ▼
       video_results             live_results
                                        │
                                        │ cameraId
                                        ▼
                                   cameras
```

---

# 11. All Eight Schema Changes

## Change 1 — Move `mode` from Sport to Task

**Before:**

```text
Sport.mode
```

**After:**

```text
Task.mode
```

**Reason:** a sport can be assessed through video or camera, so the assessment method belongs to the individual Task.

---

## Change 2 — Remove `mode` from Sport

`Sport` now contains only:

```text
code
name
scoringConfig
```

It no longer determines whether assessment is video-based or camera-based.

---

## Change 3 — Add `mode` to Task

Every Task must specify:

```text
mode = "video" | "camera"
```

This makes the assessment method explicit and queryable without inferring it through another collection.

---

## Change 4 — Attach `cameraId` to Task according to `mode`

```text
mode="video"
    cameraId = null

mode="camera"
    cameraId = required
```

This prevents video Tasks from having an unnecessary camera dependency.

---

## Change 5 — Keep `sportId` in both Result collections as denormalized data

Both:

```text
video_results.sportId
live_results.sportId
```

remain present.

However:

> `Task` is the canonical source of the relationship between a Result and its Sport.

The duplicated `sportId` exists for faster queries and indexing.

---

## Change 6 — Treat `enrollments.taskScores` as a cache

The authoritative score belongs to Result:

```text
video_results.aiScore/finalScore
live_results.score
```

`enrollments.taskScores` is only a read-optimization/cache.

---

## Change 7 — Treat `courses.studentTotal` as a counter/cache

The authoritative enrollment relationship is:

```text
enrollments
```

`courses.studentTotal` exists to avoid counting enrollment documents for common UI queries.

It should be maintained atomically with enrollment changes and periodically rebuildable.

---

## Change 8 — Make `Task = Sport + Mode` the main relationship

The domain model becomes:

```text
Sport
  = what sport?

Task
  = which assessment of that sport?
  + how is it assessed?

Result
  = what did this student achieve on that Task?
```

This cleanly separates **sport definition**, **assessment definition**, and **assessment result**.

---

# 12. Data Consistency Rules

The backend should enforce these invariants:

1. `Task.mode ∈ {"video", "camera"}`.
2. `Task.mode == "video"` ⇒ `Task.cameraId == null`.
3. `Task.mode == "camera"` ⇒ `Task.cameraId != null`.
4. `video_results` may only reference Tasks with `mode="video"`.
5. `live_results` may only reference Tasks with `mode="camera"`.
6. `video_results.sportId == Task.sportId`.
7. `live_results.sportId == Task.sportId`.
8. `live_results.cameraId` should match the Task's configured `cameraId`.
9. Result collections are the authoritative source for assessment scores.
10. `enrollments.taskScores` is a cache and may be rebuilt from Results.
11. `enrollments` is the authoritative source for Course membership.
12. `courses.studentTotal` is a counter/cache and may be rebuilt from `enrollments`.

---

# 13. Recommended Query Paths

### Find all video assessments for a sport

```js
db.video_results.find({
  sportId: "<sportId>"
})
```

The denormalized `sportId` makes this query direct.

### Find the Sport for a Result

Canonical path:

```text
Result.taskId
    ↓
Task.sportId
    ↓
Sport
```

The Result's `sportId` can be used as a fast-path query value, but should remain consistent with Task.

### Find a student's score for a Task

Fast UI path:

```text
Enrollment.taskScores[taskId]
```

Authoritative verification:

```text
video_results / live_results
```

depending on `Task.mode`.

### Count students in a Course

Fast UI path:

```text
Course.studentTotal
```

Authoritative/audit path:

```text
count(enrollments where courseId = ...)
```

---

# 14. Final Domain Model

```text
                    SPORT
             "What sport is this?"
                       │
                       │ sportId
                       ▼
                    TASK
          "What assessment is this?"
                       │
                 ┌─────┴─────┐
                 │           │
              VIDEO        CAMERA
                 │           │
                 ▼           ▼
          VIDEO RESULT   LIVE RESULT
                 │           │
                 └─────┬─────┘
                       │
                  student's
                    result
                       │
                       ▼
                 ENROLLMENT
             progress/cache data
                       │
                       ▼
                    COURSE
              course/class context
```

The resulting architecture keeps the canonical relationships normalized while deliberately using two controlled denormalizations/caches for high-frequency reads:

```text
Result.sportId
    → denormalized relationship for query performance

Enrollment.taskScores
    → score cache

Course.studentTotal
    → enrollment-count cache
```

The source of truth remains:

```text
Task      → defines assessment
Sport     → defines sport/scoring configuration
Results   → define actual assessment scores
Enrollment → defines course membership
```
