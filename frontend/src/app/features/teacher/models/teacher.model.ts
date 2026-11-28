export type ClassStatus = 'in_progress' | 'completed';

export interface GradingFormula {
  attendance_weight: number;
  process_weight: number;
  exam_weight: number;
  practice_tasks_count?: number;
}

export interface TeacherSemesterSummary {
  code: string;
  name: string;
  academic_year: string;
  term: number;
  total_sports: number;
  total_classes: number;
  total_students: number;
  active_classes: number;
  is_current: boolean;
}

export interface TeacherCourseItem {
  id: string;
  code?: string;
  name: string;
  student_total: number;
  sport_id?: string;
  sport_name?: string;
  sport_code?: string;
  semester?: string;
  semester_name?: string;
  academic_year?: string;
  term?: number;
  status: ClassStatus;
  is_grade_locked: boolean;
  allow_practice_submission: boolean;
  allow_exam_submission: boolean;
  start_date?: string;
  end_date?: string;
  exam_date?: string;
}

export interface TeacherCourseDetail extends TeacherCourseItem {
  desc?: string;
  teacher_id: string;
  teacher_name: string;
  grade_locked_at?: string;
  grading_formula: GradingFormula;
  total_weeks: number;
  total_tasks: number;
}

export type TaskKind = 'regular' | 'midterm' | 'final';
export type GradingMethod = 'highest' | 'latest' | 'average';

export interface GradebookTaskItem {
  id: string;
  title: string;
  category: 'practice' | 'exam';
  kind: TaskKind;
  description?: string;
  grading_method?: GradingMethod;
  /** Thời lượng video tối đa (giây). */
  time_limit?: number;
  open_time?: string;
  close_time?: string;
  is_locked: boolean;
  submitted_count: number;
  /** Bài AI đã chấm nhưng GV chưa xác nhận. */
  pending_review_count: number;
  instruction_video_url?: string;
  /** Cách quay: trực diện (VideoMAE) hoặc đối kháng (YOLO26s). */
  recording_mode: RecordingMode;
  target_zone?: TargetZone | null;
}

export type RecordingMode = 'direct' | 'match';

/** Vùng đích trên nửa sân đối phương (bài đối kháng). */
export type TargetZone = 'full' | 'kitchen' | 'deep' | 'service_left' | 'service_right';

export const TARGET_ZONE_LABELS: Record<TargetZone, string> = {
  full: 'Cả nửa sân đối phương',
  kitchen: 'Vùng cấm vô lê (Kitchen) – bài Dink',
  deep: 'Sau vùng cấm vô lê – bài đánh sâu',
  service_left: 'Ô giao bóng bên trái (nhìn từ camera)',
  service_right: 'Ô giao bóng bên phải (nhìn từ camera)'
};

/** Dữ liệu form tạo / sửa bài kiểm tra. */
export interface TaskUpsert {
  title: string;
  kind: TaskKind;
  description?: string | null;
  grading_method: GradingMethod;
  time_limit?: number | null;
  open_time?: string | null;
  close_time?: string | null;
  is_locked: boolean;
  recording_mode: RecordingMode;
  target_zone?: TargetZone | null;
}

export interface ExamEligibility {
  enabled: boolean;
  min_attendance_score: number;
  min_process_score: number;
}

export type AttendanceState = 'present' | 'late' | 'excused' | 'absent';

export interface AttendanceSession {
  id: string;
  date: string;
  title?: string;
  records: { [userId: string]: AttendanceState };
}

/** Một lượt nộp bài kiểm tra cho GV duyệt. */
export interface TeacherSubmission {
  id: string;
  user_id: string;
  student_code?: string;
  student_name?: string;
  attempt_no: number;
  submitted_at?: string;
  status: string;
  error?: string;
  duration_sec?: number;
  metrics: { [key: string]: any };
  ai_score?: number;
  ai_comment?: string;
  final_score?: number;
  teacher_comment?: string;
  graded_at?: string;
}

export interface StudentGrades {
  attendance_score?: number;
  process_score?: number;
  exam_score?: number;
  final_score?: number;
  letter_grade?: string;
  is_passed?: boolean;
  is_eligible?: boolean;
}

export interface GradebookStudentItem {
  enrollment_id: string;
  user_id: string;
  student_code?: string;
  student_name?: string;
  student_email?: string;
  gender?: string;
  status: 'active' | 'dropped';
  progress_percent: number;
  task_scores: { [key: string]: number | undefined };
  /** Điểm GV nhập tay, ưu tiên hơn điểm tính từ bài nộp. */
  task_score_overrides: { [key: string]: number };
  grades: StudentGrades;
  note?: string;
}

export interface GradebookResponse {
  course_id: string;
  is_grade_locked: boolean;
  formula: GradingFormula;
  exam_eligibility: ExamEligibility;
  /** Chuyên cần đang tính tự động từ điểm danh theo buổi. */
  attendance_from_sessions: boolean;
  task_list: GradebookTaskItem[];
  students: GradebookStudentItem[];
}

