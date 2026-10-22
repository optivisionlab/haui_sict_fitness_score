export interface AssessmentAttempt {
  attemptNo: number;
  date: string;
  duration?: string;
  score?: number;
  pending?: boolean;
  videoUrl?: string;
  videoResultId?: string;
  aiFeedback?: string;
  isExamSubmission?: boolean;
}

export interface AssessmentItem {
  id: string; // 'tx1' | 'tx2' | 'giua-ky' | 'cuoi-ky'
  name: string;
  type: 'tx1' | 'tx2' | 'midterm' | 'final';
  category?: 'practice' | 'exam';
  gradingMethod: string;
  timeLimit: string;
  openTime: string;
  closeTime: string;
  status: 'graded' | 'pending' | 'not_submitted' | 'locked';
  score?: number;
  aiPredictedScore?: number;
  guidelines?: string;
  maxAttempts?: number; // 1 nếu là bài kiểm tra, undefined/lớn hơn nếu là luyện tập
  attempts: AssessmentAttempt[];
  practiceAttempts?: AssessmentAttempt[];
  examAttempt?: AssessmentAttempt | null;
  isExamSubmitted?: boolean;
}

export interface CourseGradesSummary {
  attendanceScore?: number;
  processScore?: number;
  examScore?: number;
  finalScore?: number;
  kt1Score?: number;
  kt2Score?: number;
  hasAnyGrade: boolean;
}

export interface Course {
  id: string;
  name: string;
  code: string;
  teacher: string;
  startDate: string;
  endDate: string;
  examDate: string;
  progress: number;
  status: 'active' | 'done';
  iconType: 'pickleball' | 'chay';
  averageScore?: number;
  gradesSummary?: CourseGradesSummary;
}

export interface CourseDetailInfo {
  id: string;
  title: string;
  teacher: string;
  dates: string;
  examDate: string;
  progress: number;
  code: string;
  desc: string;
  thumbClass: string;
  thumbIcon: 'pickleball' | 'chay';
  averageScore?: number;
  gradesSummary?: CourseGradesSummary;
  assessments: AssessmentItem[];
}
