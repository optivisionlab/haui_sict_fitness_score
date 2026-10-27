export interface AssessmentAttempt {
  attemptNo: number;
  date: string;
  duration?: string;
  score?: number;
  aiScore?: number;
  aiFeedback?: string;
  pending?: boolean;
  failed?: boolean;
  error?: string;
  feedback?: string;
  videoUrl?: string;
  videoResultId?: string;
}

export interface AssessmentItem {
  id: string; // 'kt1-practice' | 'kt1-exam' | 'kt2-practice' | 'kt2-exam' | 'final-exam'
  name: string;
  type: 'tx1' | 'tx2' | 'midterm' | 'final';
  mode: 'practice' | 'exam'; // 'practice': nộp nhiều lần, lấy điểm cao nhất; 'exam': nộp nhiều lần, lấy điểm lần nộp gần nhất
  groupTitle?: string; // 'KT1: Kỹ thuật 1' | 'KT2: Kỹ thuật 2' | 'Thi: Kết thúc học phần'
  technicalRequirements?: string;
  gradingMethod: string;
  timeLimit: string;
  openTime: string;
  closeTime: string;
  status: 'graded' | 'pending' | 'not_submitted' | 'locked';
  score?: number;
  aiScore?: number;
  attempts: AssessmentAttempt[];
}

export interface CourseGrades {
  kt1?: number;
  kt2?: number;
  dqt?: number;
  exam?: number;
  final?: number;
  letterGrade?: string;
}

export interface Course {
  id: string;
  name: string;
  code?: string;
  teacher: string;
  startDate: string;
  endDate: string;
  examDate: string;
  progress: number;
  status: 'active' | 'done';
  iconType: 'pickleball' | 'chay';
  averageScore?: number;
  grades?: CourseGrades;
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
  grades?: CourseGrades;
  assessments: AssessmentItem[];
}

