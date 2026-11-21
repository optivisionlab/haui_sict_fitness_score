import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, forkJoin, map } from 'rxjs';
import { environment } from '../../../environments/environment';
import { ApiResponse, User, UserRole } from '../models/auth.model';

export interface PaginatedResult<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface SportScoringConfig {
  metrics_fields?: string[];
  formula?: string | null;
  thresholds?: Record<string, number>;
}

export interface Sport {
  id: string;
  code: string;
  name: string;
  mode: 'video' | 'camera';
  scoring_config?: SportScoringConfig;
  created_at?: string;
  updated_at?: string;
}

export interface SportCreateRequest {
  code: string;
  name: string;
  mode: 'video' | 'camera';
  scoring_config?: SportScoringConfig;
}

export interface Course {
  id: string;
  key?: string;
  code?: string;
  name: string;
  desc?: string;
  teacher_id: string;
  teacher_name?: string;
  sport_id?: string;
  sport_name?: string;
  sport_code?: string;
  semester?: string;
  semester_name?: string;
  academic_year?: string;
  term?: number;
  student_total?: number;
  status?: string;
  start_date?: string;
  end_date?: string;
  exam_date?: string;
  created_at?: string;
}

export interface CourseCreateRequest {
  code?: string;
  name: string;
  desc?: string;
  teacher_id: string;
  teacher_name?: string;
  sport_id?: string;
  sport_name?: string;
  sport_code?: string;
  semester?: string;
  semester_name?: string;
  academic_year?: string;
  term?: number;
  key?: string;
  status?: string;
}

export interface Enrollment {
  id: string;
  user_id: string;
  course_id: string;
  user_name?: string;
  student_code?: string;
  course_name?: string;
  course_code?: string;
  teacher_name?: string;
  status?: string;
  attendance_score?: number | null;
  practice_score?: number | null;
  exam_score?: number | null;
  final_grade?: number | null;
  enrolled_at?: string;
}

export interface StudentImportResult {
  enrolled: number;
  already_enrolled: number;
  errors: string[];
}

export interface DashboardStats {
  totalUsers: number;
  totalStudents: number;
  totalTeachers: number;
  totalSports: number;
  totalCourses: number;
}


/**
 * Backend bọc kết quả trong { success, code, message, data } và trả khóa camelCase,
 * còn các màn hình Admin dùng khóa snake_case. Hàm này bóc lớp `data` và bổ sung
 * khóa snake_case song song với khóa gốc (giữ nguyên khóa camelCase).
 */
function withSnakeKeys(value: any): any {
  if (Array.isArray(value)) return value.map(withSnakeKeys);
  if (value === null || typeof value !== 'object') return value;
  const out: Record<string, any> = {};
  for (const [key, v] of Object.entries(value)) {
    const converted = withSnakeKeys(v);
    out[key] = converted;
    const snake = key.replace(/[A-Z]/g, (c) => '_' + c.toLowerCase());
    if (snake !== key && !(snake in value)) out[snake] = converted;
  }
  return out;
}

function fromApi<T>(res: any): T {
  const body = res && typeof res === 'object' && 'data' in res && 'success' in res ? res.data : res;
  return withSnakeKeys(body) as T;
}

@Injectable({
  providedIn: 'root'
})
export class AdminService {
  private http = inject(HttpClient);
  private baseUrl = environment.apiUrl;

  // ==================== DASHBOARD STATS ====================
  getDashboardStats(): Observable<DashboardStats> {
    return forkJoin({
      students: this.http.get<PaginatedResult<User>>(`${this.baseUrl}/users`, { params: { role: 'student', page: '1', page_size: '1' } }),
      teachers: this.http.get<PaginatedResult<User>>(`${this.baseUrl}/users`, { params: { role: 'teacher', page: '1', page_size: '1' } }),
      admins: this.http.get<PaginatedResult<User>>(`${this.baseUrl}/users`, { params: { role: 'admin', page: '1', page_size: '1' } }),
      sports: this.http.get<PaginatedResult<Sport>>(`${this.baseUrl}/sports`, { params: { page: '1', page_size: '1' } }),
      courses: this.http.get<PaginatedResult<Course>>(`${this.baseUrl}/courses`, { params: { page: '1', page_size: '1' } }),
    }).pipe(
      map((raw) => {
        const { students, teachers, admins, sports, courses } = {
          students: fromApi<PaginatedResult<User>>(raw.students),
          teachers: fromApi<PaginatedResult<User>>(raw.teachers),
          admins: fromApi<PaginatedResult<User>>(raw.admins),
          sports: fromApi<PaginatedResult<Sport>>(raw.sports),
          courses: fromApi<PaginatedResult<Course>>(raw.courses)
        };
        const studentCount = students?.total || 0;
        const teacherCount = teachers?.total || 0;
        return {
          totalStudents: studentCount,
          totalTeachers: teacherCount,
          totalUsers: studentCount + teacherCount + (admins?.total || 0),
          totalSports: sports?.total || 0,
          totalCourses: courses?.total || 0
        };
      })
    );
  }

  // ==================== USERS MANAGEMENT ====================
  getUsers(role?: string, page: number = 1, pageSize: number = 20): Observable<PaginatedResult<User>> {
    let params = new HttpParams()
      .set('page', page.toString())
      .set('page_size', pageSize.toString());

    if (role && role !== 'all') {
      params = params.set('role', role);
    }

    return this.http.get<PaginatedResult<User>>(`${this.baseUrl}/users`, { params }).pipe(map((r) => fromApi<any>(r)));
  }

  createUser(data: {
    email: string;
    password?: string;
    name: string;
    role: UserRole;
    user_code?: string;
    phone_number?: string;
  }): Observable<ApiResponse<User>> {
    return this.http.post<ApiResponse<User>>(`${this.baseUrl}/auth/register`, data).pipe(map((r) => fromApi<any>(r)));
  }

  updateUser(userId: string, data: Partial<User>): Observable<User> {
    return this.http.put<User>(`${this.baseUrl}/users/${userId}`, data).pipe(map((r) => fromApi<any>(r)));
  }

  deleteUser(userId: string): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(`${this.baseUrl}/users/${userId}`).pipe(map((r) => fromApi<any>(r)));
  }

  // ==================== SPORTS MANAGEMENT ====================
  getSports(page: number = 1, pageSize: number = 50): Observable<PaginatedResult<Sport>> {
    const params = new HttpParams()
      .set('page', page.toString())
      .set('page_size', pageSize.toString());
    return this.http.get<PaginatedResult<Sport>>(`${this.baseUrl}/sports`, { params }).pipe(map((r) => fromApi<any>(r)));
  }

  createSport(data: SportCreateRequest): Observable<Sport> {
    return this.http.post<Sport>(`${this.baseUrl}/sports`, data).pipe(map((r) => fromApi<any>(r)));
  }

  updateSport(sportId: string, data: Partial<SportCreateRequest>): Observable<Sport> {
    return this.http.put<Sport>(`${this.baseUrl}/sports/${sportId}`, data).pipe(map((r) => fromApi<any>(r)));
  }

  deleteSport(sportId: string): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(`${this.baseUrl}/sports/${sportId}`).pipe(map((r) => fromApi<any>(r)));
  }

  // ==================== COURSES / CLASSES MANAGEMENT ====================
  getCourses(page: number = 1, pageSize: number = 50, teacherId?: string): Observable<PaginatedResult<Course>> {
    let params = new HttpParams()
      .set('page', page.toString())
      .set('page_size', pageSize.toString());
    if (teacherId) {
      params = params.set('teacher_id', teacherId);
    }
    return this.http.get<PaginatedResult<Course>>(`${this.baseUrl}/courses`, { params }).pipe(map((r) => fromApi<any>(r)));
  }

  getCourseDetail(courseId: string): Observable<Course> {
    return this.http.get<Course>(`${this.baseUrl}/courses/${courseId}`).pipe(map((r) => fromApi<any>(r)));
  }

  createCourse(data: CourseCreateRequest): Observable<Course> {
    return this.http.post<Course>(`${this.baseUrl}/courses`, data).pipe(map((r) => fromApi<any>(r)));
  }

  updateCourse(courseId: string, data: Partial<CourseCreateRequest>): Observable<Course> {
    return this.http.put<Course>(`${this.baseUrl}/courses/${courseId}`, data).pipe(map((r) => fromApi<any>(r)));
  }

  deleteCourse(courseId: string): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(`${this.baseUrl}/courses/${courseId}`).pipe(map((r) => fromApi<any>(r)));
  }

  // ==================== ENROLLMENTS MANAGEMENT ====================
  getCourseEnrollments(courseId: string, page: number = 1, pageSize: number = 100): Observable<PaginatedResult<Enrollment>> {
    const params = new HttpParams()
      .set('course_id', courseId)
      .set('page', page.toString())
      .set('page_size', pageSize.toString());
    return this.http.get<PaginatedResult<Enrollment>>(`${this.baseUrl}/enrollments`, { params }).pipe(
      map((r) => fromApi<PaginatedResult<any>>(r)),
      // Backend lưu điểm trong `grades` và tên SV ở `studentName`; trải phẳng cho bảng của Admin
      map((page) => ({
        ...page,
        items: (page.items || []).map((e: any) => ({
          ...e,
          user_name: e.user_name ?? e.student_name,
          attendance_score: e.grades?.attendance_score ?? null,
          practice_score: e.grades?.process_score ?? null,
          exam_score: e.grades?.exam_score ?? null,
          final_grade: e.grades?.final_score ?? null,
          enrolled_at: e.created_at
        }))
      }))
    );
  }

  enrollStudent(courseId: string, userId: string): Observable<Enrollment> {
    return this.http.post<Enrollment>(`${this.baseUrl}/enrollments`, {
      course_id: courseId,
      user_id: userId
    }).pipe(map((r) => fromApi<any>(r)));
  }

  removeEnrollment(enrollmentId: string): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(`${this.baseUrl}/enrollments/${enrollmentId}`).pipe(map((r) => fromApi<any>(r)));
  }

  // ==================== IMPORT ====================
  /** Ghi danh hàng loạt sinh viên (đã có tài khoản) từ file .xlsx / .csv. */
  importStudents(courseId: string, file: File): Observable<StudentImportResult> {
    const form = new FormData();
    form.append('file', file);
    return this.http.post(`${this.baseUrl}/courses/${courseId}/import-students`, form).pipe(map((r) => fromApi<StudentImportResult>(r)));
  }
}
