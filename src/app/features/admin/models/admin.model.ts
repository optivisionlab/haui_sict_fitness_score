export type ExamConditionType = 'eligible' | 'ineligible' | 'pending';

export interface WeeklyRecord {
  week: string;
  period: string;
  practiceCompleted: string | number;
  liveClassCompleted: string | number;
  testCompleted: string | number;
  examCondition: string;
}

export interface AdminStudentItem {
  id: string;
  studentCode: string;
  fullName: string;
  majorClass: string;
  subjectName: string;
  classCode: string;
  startDate: string;
  regularGradeDeadline: string;
  liveClassCompleted: number;
  liveClassTotal: number;
  practiceCompleted: number;
  practiceTotal: number;
  testCompleted: number;
  testTotal: number;
  examCondition: ExamConditionType;
  examConditionNote?: string;
  finalScore?: number;
  weeklyDetails: WeeklyRecord[];
}

export interface AdminCourseClass {
  id: string;
  subjectName: string;
  subjectCode: string;
  classCode: string;
  teacher: string;
  startDate: string;
  endDate: string;
  regularGradeDeadline: string;
  totalStudents: number;
  eligibleCount: number;
  status: 'ongoing' | 'completed' | 'upcoming';
}

export interface AdminDashboardKpi {
  totalStudents: number;
  totalClasses: number;
  eligibleRate: number;
  pendingReviewCount: number;
}
