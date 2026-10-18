import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpEvent, HttpHeaders, HttpParams, HttpResponse } from '@angular/common/http';
import { Observable } from 'rxjs';
import { concatMap, map, switchMap } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import { ApiResponse } from '../models/auth.model';
import {
  Paginated,
  VideoResult,
  VideoResultFilter,
  VideoResultStatusInfo,
  VideoUploadPayload,
  VideoUploadUrl
} from '../models/video-result.model';

@Injectable({
  providedIn: 'root'
})
export class VideoResultService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/video-results`;

  /** Upload directly to MinIO, then confirm the object with the backend. */
  uploadVideo(payload: VideoUploadPayload): Observable<HttpEvent<ApiResponse<VideoResult>>> {
    return this.http.post<ApiResponse<VideoUploadUrl>>(`${this.baseUrl}/upload-url`, {
      task_id: payload.exercise_id,
      course_id: payload.course_id,
      file_name: payload.file.name,
      content_type: payload.file.type || 'application/octet-stream',
      file_size: payload.file.size
    }).pipe(
      switchMap((response) => {
        const upload = response.data;
        if (!upload?.uploadUrl || !upload.uploadId) {
          throw new Error('Backend không trả về thông tin upload hợp lệ.');
        }

        return this.http.put(upload.uploadUrl, payload.file, {
          headers: new HttpHeaders({ 'Content-Type': payload.file.type || 'application/octet-stream' }),
          observe: 'events',
          reportProgress: true,
          responseType: 'text'
        }).pipe(
          concatMap((event) => {
            if (event instanceof HttpResponse) {
              return this.http.post<ApiResponse<VideoResult>>(`${this.baseUrl}/confirm-upload`, {
                upload_id: upload.uploadId
              }).pipe(map((confirmed) => new HttpResponse({
                body: confirmed,
                status: 200,
                url: `${this.baseUrl}/confirm-upload`
              })));
            }
            return [event as HttpEvent<ApiResponse<VideoResult>>];
          })
        );
      })
    );
  }

  /**
   * Lấy danh sách kết quả video nộp bài theo bộ lọc (sinh viên, bài tập, lớp)
   */
  getVideoResults(filters?: VideoResultFilter): Observable<ApiResponse<Paginated<VideoResult>>> {
    let params = new HttpParams();
    if (filters?.student_id) params = params.set('student_id', filters.student_id);
    if (filters?.exercise_id) params = params.set('exercise_id', filters.exercise_id);
    if (filters?.class_id) params = params.set('class_id', filters.class_id);
    if (filters?.status) params = params.set('status', filters.status);
    if (filters?.page !== undefined) params = params.set('page', filters.page.toString());
    if (filters?.page_size !== undefined) params = params.set('page_size', filters.page_size.toString());

    return this.http.get<ApiResponse<Paginated<VideoResult>>>(this.baseUrl, { params });
  }

  /**
   * Trạng thái chấm điểm của một bài nộp (dùng để polling sau khi upload)
   */
  getSubmissionStatus(id: string): Observable<ApiResponse<VideoResultStatusInfo>> {
    return this.http.get<ApiResponse<VideoResultStatusInfo>>(`${this.baseUrl}/${id}/status`);
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
  getVideoStreamUrl(id: string): Observable<ApiResponse<{ videoUrl: string; expiresInSeconds: number }>> {
    return this.http.get<ApiResponse<{ videoUrl: string; expiresInSeconds: number }>>(`${this.baseUrl}/${id}/video-url`);
  }
}
