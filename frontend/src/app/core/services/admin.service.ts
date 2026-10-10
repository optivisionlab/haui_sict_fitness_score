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

export interface DashboardStats {
  totalUsers: number;
  totalStudents: number;
  totalTeachers: number;
  totalSports: number;
  totalCourses: number;
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
      sports: this.http.get<PaginatedResult<Sport>>(`${this.baseUrl}/sports`, { params: { page: '1', page_size: '1' } }),
      courses: this.http.get<PaginatedResult<Course>>(`${this.baseUrl}/courses`, { params: { page: '1', page_size: '1' } }),
    }).pipe(
      map(({ students, teachers, sports, courses }) => {
        const studentCount = students?.total || 0;
        const teacherCount = teachers?.total || 0;
        return {
          totalStudents: studentCount,
          totalTeachers: teacherCount,
          totalUsers: studentCount + teacherCount + 1, // + 1 admin
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

    return this.http.get<PaginatedResult<User>>(`${this.baseUrl}/users`, { params });
  }

  createUser(data: {
    email: string;
    password?: string;
    name: string;
    role: UserRole;
    user_code?: string;
    phone_number?: string;
  }): Observable<ApiResponse<User>> {
    return this.http.post<ApiResponse<User>>(`${this.baseUrl}/auth/register`, data);
  }

  updateUser(userId: string, data: Partial<User>): Observable<User> {
    return this.http.put<User>(`${this.baseUrl}/users/${userId}`, data);
  }

  deleteUser(userId: string): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(`${this.baseUrl}/users/${userId}`);
  }

  // ==================== SPORTS MANAGEMENT ====================
  getSports(page: number = 1, pageSize: number = 50): Observable<PaginatedResult<Sport>> {
    const params = new HttpParams()
      .set('page', page.toString())
      .set('page_size', pageSize.toString());
    return this.http.get<PaginatedResult<Sport>>(`${this.baseUrl}/sports`, { params });
  }

  createSport(data: SportCreateRequest): Observable<Sport> {
    return this.http.post<Sport>(`${this.baseUrl}/sports`, data);
  }

  updateSport(sportId: string, data: Partial<SportCreateRequest>): Observable<Sport> {
    return this.http.put<Sport>(`${this.baseUrl}/sports/${sportId}`, data);
  }

  deleteSport(sportId: string): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(`${this.baseUrl}/sports/${sportId}`);
  }

  // ==================== COURSES / CLASSES MANAGEMENT ====================
  getCourses(page: number = 1, pageSize: number = 50, teacherId?: string): Observable<PaginatedResult<Course>> {
    let params = new HttpParams()
      .set('page', page.toString())
      .set('page_size', pageSize.toString());
    if (teacherId) {
      params = params.set('teacher_id', teacherId);
    }
    return this.http.get<PaginatedResult<Course>>(`${this.baseUrl}/courses`, { params });
  }

  getCourseDetail(courseId: string): Observable<Course> {
    return this.http.get<Course>(`${this.baseUrl}/courses/${courseId}`);
  }

  createCourse(data: CourseCreateRequest): Observable<Course> {
    return this.http.post<Course>(`${this.baseUrl}/courses`, data);
  }

  updateCourse(courseId: string, data: Partial<CourseCreateRequest>): Observable<Course> {
    return this.http.put<Course>(`${this.baseUrl}/courses/${courseId}`, data);
  }

  deleteCourse(courseId: string): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(`${this.baseUrl}/courses/${courseId}`);
  }

  // ==================== ENROLLMENTS MANAGEMENT ====================
  getCourseEnrollments(courseId: string, page: number = 1, pageSize: number = 100): Observable<PaginatedResult<Enrollment>> {
    const params = new HttpParams()
      .set('course_id', courseId)
      .set('page', page.toString())
      .set('page_size', pageSize.toString());
    return this.http.get<PaginatedResult<Enrollment>>(`${this.baseUrl}/enrollments`, { params });
  }

  enrollStudent(courseId: string, userId: string): Observable<Enrollment> {
    return this.http.post<Enrollment>(`${this.baseUrl}/enrollments`, {
      course_id: courseId,
      user_id: userId
    });
  }

  removeEnrollment(enrollmentId: string): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(`${this.baseUrl}/enrollments/${enrollmentId}`);
  }
}
