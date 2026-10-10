import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpEvent, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { ApiResponse } from '../models/auth.model';
import { VideoResult, VideoResultFilter, VideoUploadPayload } from '../models/video-result.model';

@Injectable({
  providedIn: 'root'
})
export class VideoResultService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/video-results`;

  /**
   * Tải video lên server với theo dõi tiến trình (Progress tracking)
   */
  uploadVideo(payload: VideoUploadPayload): Observable<HttpEvent<ApiResponse<VideoResult>>> {
    const formData = new FormData();
    formData.append('file', payload.file);
    formData.append('student_id', payload.student_id);
    formData.append('exercise_id', payload.exercise_id);

    if (payload.class_id) {
      formData.append('class_id', payload.class_id);
    }
    if (payload.course_id) {
      formData.append('course_id', payload.course_id);
    }

    return this.http.post<ApiResponse<VideoResult>>(`${this.baseUrl}/upload`, formData, {
      reportProgress: true,
      observe: 'events'
    });
  }

  /**
   * Lấy danh sách kết quả video nộp bài theo bộ lọc (sinh viên, bài tập, lớp)
   */
  getVideoResults(filters?: VideoResultFilter): Observable<ApiResponse<VideoResult[]>> {
    let params = new HttpParams();
    if (filters?.student_id) params = params.set('student_id', filters.student_id);
    if (filters?.exercise_id) params = params.set('exercise_id', filters.exercise_id);
    if (filters?.class_id) params = params.set('class_id', filters.class_id);
    if (filters?.status) params = params.set('status', filters.status);
    if (filters?.skip !== undefined) params = params.set('skip', filters.skip.toString());
    if (filters?.limit !== undefined) params = params.set('limit', filters.limit.toString());

    return this.http.get<ApiResponse<VideoResult[]>>(this.baseUrl, { params });
  }

  /**
   * Lấy chi tiết một bài nộp video theo ID
   */
  getVideoResultById(id: string): Observable<ApiResponse<VideoResult>> {
    return this.http.get<ApiResponse<VideoResult>>(`${this.baseUrl}/${id}`);
  }

  /**
   * Lấy link presigned trực tiếp để phát video từ MinIO
   */
  getVideoStreamUrl(id: string): Observable<ApiResponse<{ video_url: string; expires_in: number }>> {
    return this.http.get<ApiResponse<{ video_url: string; expires_in: number }>>(`${this.baseUrl}/${id}/video-url`);
  }
}
