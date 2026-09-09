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
  attempts: TaskAttempt[];
  laps?: RunLap[];
}
