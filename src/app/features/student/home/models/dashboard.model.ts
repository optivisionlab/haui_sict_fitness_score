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
  subjectName: string;
  subjectCode: string;
  room: string;
  timeSlot: string;
  period: string;
  instructor: string;
  status: 'upcoming' | 'ongoing' | 'completed';
}

export interface AssignmentTask {
  id: string;
  title: string;
  courseName: string;
  dueDate: string;
  status: 'urgent' | 'pending' | 'submitted';
  score?: number;
}
