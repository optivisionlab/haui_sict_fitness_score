export interface StudentSummary {
  fullName: string;
  studentId: string;
  avatarUrl: string;
  faculty: string;
  major: string;
  classCode: string;
  semester: string;
  gpa: number;
  creditsEarned: number;
  trainingScore: number;
}

export interface ActiveCourseSummary {
  id: string;
  title: string;
  code: string;
  instructor: string;
  progress: number;
  completedLessons: number;
  totalLessons: number;
  currentLesson: string;
  coverImage: string;
  category: string;
}

export interface ScheduleItem {
  id: string;
  dayOfWeek: string;
  date: string;
  sessionPeriod: string;
  subjectName: string;
  instructor: string;
  room: string;
}

export interface AssignmentTask {
  id: string;
  title: string;
  courseName: string;
  dueDate: string;
  status: 'urgent' | 'pending' | 'submitted';
  score?: number;
}
