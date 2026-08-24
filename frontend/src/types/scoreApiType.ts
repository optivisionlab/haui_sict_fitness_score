export interface ScoreResult {
  result_id: number;
  exam_id: number;
  exam_title: string;
  exam_description: string;
  exam_date: string | null;
  start_time: string;
  end_time: string;
  avg_speed: number | null;
}
