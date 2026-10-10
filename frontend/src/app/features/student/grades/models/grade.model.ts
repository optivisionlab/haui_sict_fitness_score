export interface GradeItemDetail {
  id: string;
  name: string;
  type: 'AI Tracking' | 'Giáo viên chấm' | 'Thực hành';
  date: string;
  score?: number | null;
  maxScore?: number;
  result?: string;
  status: 'graded' | 'pending';
}

export interface GradeWeekDetail {
  week: string;
  period: string;
  practiceCompleted?: number | string;
  liveClassCompleted?: number | string;
  testCompleted?: number | string;
  examCondition?: string;
}

export interface GradeWeekSummary {
  period: string;
  practiceCompleted: string;
  liveClassCompleted: string;
  testCompleted: string;
  examCondition?: string;
}

export interface GradeSubject {
  id: string;
  name: string;
  classCode: string;
  teacher?: string;
  regularScore?: number | null;     // Điểm thường xuyên
  tx1Score?: number | null;         // Điểm TX 1
  tx2Score?: number | null;         // Điểm TX 2
  finalScore?: number | null;       // Điểm thi KTHP
  score?: number | null;            // Điểm số (Thang điểm 10)
  letterGrade?: string | null;      // Điểm tổng kết bằng chữ (A, B+, B, C, D, F)
  averageScore?: number | null;     // Điểm trung bình
  result?: 'pass' | 'fail' | 'studying'; // Kết quả: Đạt / Chưa đạt / Đang học
  status: 'active' | 'completed';
  examCondition?: 'eligible' | 'ineligible' | null;
  startDate?: string;
  regularGradeDeadline?: string;
  liveClassCompleted?: number;
  practiceCompleted?: number;
  testCompleted?: number | string;
  weeklyDetails?: GradeWeekDetail[];
  summary?: GradeWeekSummary;
  details?: GradeItemDetail[];
}
