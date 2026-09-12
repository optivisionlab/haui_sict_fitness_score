export interface CourseScore {
  label: string;
  score: number;
}

export interface Course {
  id: string;
  name: string;
  teacher: string;
  startDate: string;
  endDate: string;
  examDate: string;
  progress: number;
  status: 'active' | 'done';
  iconType: 'pickleball' | 'chay';
  scores?: CourseScore[];
}

export interface PracticeTaskItem {
  id: string;
  title: string;
  taskKey: string;
  requirements: string; // Yêu cầu kỹ thuật
  guide: string; // Hướng dẫn thực hiện
  deadline: string;
  canSubmitMultiple: true; // Nộp nhiều lần cho đến khi hết hạn
  submittedCount: number;
  bestScore?: number;
  aiEstimatedScore?: number; // Điểm đánh giá dự kiến từ AI
}

export interface ExamSubmitItem {
  id: string;
  title: string;
  taskKey: string;
  deadline: string;
  canSubmitMultiple: false; // Chỉ được nộp 1 lần duy nhất
  submitted: boolean;
  score?: number;
  aiEstimatedScore?: number; // Điểm đánh giá dự kiến từ AI
  isFinalExam?: boolean;
}

export interface ExamBlock {
  id: string;
  label: string; // VD: 'KT1: Kỹ thuật 1 - Giao bóng', 'Thi: Nộp bài thi kết thúc học phần'
  isFinalExam?: boolean;
  status: 'done' | 'active' | 'locked';
  practiceItem?: PracticeTaskItem; // Luyện tập (nộp nhiều lần)
  examItem: ExamSubmitItem; // Bài kiểm tra / Thi (nộp 1 lần duy nhất)
  aiEstimatedScore?: number; // Điểm đánh giá dự kiến AI của toàn bộ bài KT / Thi
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
  qlhtName: string;
  qlhtPhone: string;
  qlhtEmail: string;
  thumbClass: string;
  thumbIcon: 'pickleball' | 'chay';
  students: string[];
  studentTotal: number;
  examBlocks?: ExamBlock[];
}

export interface LessonWeek {
  label: string;
  status: 'done' | 'active' | 'locked';
  lessons: string[];
  items: LessonItem[];
}

export interface LessonItem {
  title: string;
  type: 'L' | 'P';
  typeLabel: string;
  taskKey?: string;
  graded?: boolean;
  score?: number;
}

export interface TaskAttempt {
  date: string;
  duration?: string;
  attemptNo: number;
  score?: number;
  pending?: boolean;
  aiEvaluation?: {
    accuracyRate: number;
    repCount: number;
    validCount: number;
    feedback: string;
  };
}

export interface RunLap {
  time: string;
  speed: string;
  distance: string;
  score: number;
}

export interface TaskDetail {
  courseKey: string;
  type: 'video' | 'run-test' | 'run-practice';
  title: string;
  gradingMethod: string;
  timeLimit: string;
  openTime: string;
  closeTime: string;
  canSubmitMultiple?: boolean; // false nếu là bài kiểm tra/thi
  submitted?: boolean;
  requirements?: string;
  guide?: string;
  aiEstimatedScore?: number; // Điểm đánh giá dự kiến của AI
  attempts: TaskAttempt[];
  laps?: RunLap[];
}
