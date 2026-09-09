export interface GradeSubject {
  id: string;
  name: string;
  classCode: string;
  startDate: string;
  regularGradeDeadline: string;
  liveClassCompleted: number;
  practiceCompleted: number;
  testCompleted?: number | string;
  examCondition?: 'eligible' | 'ineligible' | null;
  status: 'active' | 'completed';
  weeklyDetails?: GradeWeekDetail[];
  summary?: GradeWeekSummary;
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
