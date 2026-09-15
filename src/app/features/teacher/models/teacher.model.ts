export type ClassStatus = 'active' | 'pending_finalize' | 'finalized';

export interface ClassAssessment {
  id: string; // 'tx1' | 'tx2' | 'midterm' | 'final'
  name: string;
  type: 'tx1' | 'tx2' | 'midterm' | 'final';
  weight: number; // e.g. 10%, 20%, 30%, 40%
  gradingMethod: string;
  timeLimit: string;
  openTime: string;
  closeTime: string;
  submittedCount: number;
  totalCount: number;
  isLocked: boolean; // Khóa nộp bài cho riêng bài này
  status: 'open' | 'locked' | 'graded';
}

export interface StudentSubmission {
  attemptNo: number;
  submittedAt: string;
  videoUrl?: string;
  duration?: string;
  aiScore?: number;
  aiFeedback?: string;
  teacherScore?: number;
  teacherComment?: string;
  status: 'graded' | 'pending';
}

export interface StudentGradeRecord {
  id: string;
  studentCode: string;
  fullName: string;
  majorClass: string; // Lớp chuyên ngành ví dụ: D17CNPM1
  tx1Score: number | null;
  tx2Score: number | null;
  midtermScore: number | null;
  finalScore: number | null;
  finalAvgScore: number | null; // Điểm tổng kết hệ 10
  letterGrade: string | null; // A, B+, B, C+, C, D+, D, F
  resultStatus: 'pass' | 'fail' | 'warning' | 'pending'; // Đạt / Chưa đạt / Cảnh báo
  avatar?: string;
  submissions?: {
    [assessmentId: string]: StudentSubmission;
  };
}

export interface TeacherClass {
  id: string;
  code: string; // Ví dụ: FIT-PB01
  name: string; // Pickleball cơ bản
  semester: string; // HK1 - 2026-2027
  schedule: string; // Thứ 3, Tiết 1-3
  location: string; // Sân giáo dục thể chất A
  studentCount: number;
  maxStudents: number;
  progressSessions: number; // Ví dụ: 10/15 buổi
  totalSessions: number;
  status: ClassStatus;
  iconType: 'pickleball' | 'chay' | 'fitness';
  teacherName: string;
  teacherCode: string;
  isPracticeLocked: boolean; // Khóa tính năng luyện tập
  isSubmissionLocked: boolean; // Khóa nộp bài
  isFinalized: boolean; // Giáo viên đã chốt điểm
  finalizedAt?: string;
  finalizedBy?: string;
  assessments: ClassAssessment[];
  students: StudentGradeRecord[];
}
