export interface AssessmentAttempt {
  attemptNo: number;
  date: string;
  duration?: string;
  score?: number;
  pending?: boolean;
  videoUrl?: string;
  videoResultId?: string;
}

export interface AssessmentItem {
  id: string; // 'tx1' | 'tx2' | 'giua-ky' | 'cuoi-ky'
  name: string;
  type: 'tx1' | 'tx2' | 'midterm' | 'final';
  gradingMethod: string;
  timeLimit: string;
  openTime: string;
  closeTime: string;
  status: 'graded' | 'pending' | 'not_submitted' | 'locked';
  score?: number;
  attempts: AssessmentAttempt[];
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
  averageScore?: number;
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
  assessments: AssessmentItem[];
}
