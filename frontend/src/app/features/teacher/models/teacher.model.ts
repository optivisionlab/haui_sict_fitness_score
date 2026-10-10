export type ClassStatus = 'in_progress' | 'completed';

export interface GradingFormula {
  attendance_weight: number;
  process_weight: number;
  exam_weight: number;
  practice_tasks_count?: number;
}

export interface TeacherCourseItem {
  id: string;
  code?: string;
  name: string;
  student_total: number;
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

export interface GradebookTaskItem {
  id: string;
  title: string;
  category: 'practice' | 'exam';
}

export interface StudentGrades {
  attendance_score?: number;
  process_score?: number;
  exam_score?: number;
  final_score?: number;
  letter_grade?: string;
  is_passed?: boolean;
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
  task_scores: { [key: string]: number };
  grades: StudentGrades;
  note?: string;
}

export interface GradebookResponse {
  course_id: string;
  is_grade_locked: boolean;
  formula: GradingFormula;
  task_list: GradebookTaskItem[];
  students: GradebookStudentItem[];
}

