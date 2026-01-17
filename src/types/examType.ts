export interface ExamResult {
  result_id: number;
  user_id: number;
  full_name: string;
  exam_id: number;
  exam_title: string;
  class_id: number;
  class_name: string;
  step: number;
  start_time: string; // ISO string
  end_time: string; // ISO string
  avg_speed: number;
  created_at: string; // ISO string
}
