export type VideoResultStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface VideoResult {
  id: string;
  student_id: string;
  exercise_id: string;
  class_id?: string | null;
  course_id?: string | null;
  status: VideoResultStatus;
  video_url: string;
  file_name: string;
  file_size: number;
  content_type?: string | null;
  created_at: string;
  updated_at?: string | null;
  score?: number | null;
  feedback?: string | null;
  error_message?: string | null;
  metrics?: Record<string, any> | null;
}

export interface VideoUploadPayload {
  file: File;
  student_id: string;
  exercise_id: string;
  class_id?: string;
  course_id?: string;
}

export interface VideoResultFilter {
  student_id?: string;
  exercise_id?: string;
  class_id?: string;
  status?: string;
  skip?: number;
  limit?: number;
}
