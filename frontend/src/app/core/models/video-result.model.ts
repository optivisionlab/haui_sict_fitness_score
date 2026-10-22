export type VideoResultStatus = 'pending' | 'processing' | 'completed' | 'failed';

/** Bài nộp video — khớp VideoResultRead của backend (JSON camelCase). */
export interface VideoResult {
  id: string;
  userId: string;
  taskId: string;
  sportId?: string | null;
  attemptNo: number;
  status: VideoResultStatus;
  pending: boolean;
  videoUrl?: string | null;
  fileName?: string | null;
  fileSize?: number | null;
  contentType?: string | null;
  durationSec?: number | null;
  submittedAt: string;
  createdAt?: string | null;
  updatedAt?: string | null;
  aiScore?: number | null;
  aiComment?: string | null;
  finalScore?: number | null;
  teacherComment?: string | null;
  error?: string | null;
  metrics?: Record<string, any> | null;
}

/** Response của GET /video-results/{id}/status (polling). */
export interface VideoResultStatusInfo {
  id: string;
  pending: boolean;
  status: VideoResultStatus;
  error?: string | null;
  aiScore?: number | null;
  finalScore?: number | null;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

export interface VideoUploadPayload {
  file: File;
  exercise_id: string;
  course_id?: string;
}

export interface VideoUploadUrl {
  uploadId: string;
  resultId: string;
  objectKey: string;
  uploadUrl: string;
  expiresIn: number;
}

export interface VideoResultFilter {
  student_id?: string;
  exercise_id?: string;
  class_id?: string;
  status?: string;
  page?: number;
  page_size?: number;
}
