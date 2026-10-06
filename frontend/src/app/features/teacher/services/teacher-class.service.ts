import { Injectable, signal, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap, map, catchError, of } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { ApiResponse } from '../../../core/models/auth.model';
import { 
  TeacherCourseItem, 
  TeacherCourseDetail,
  GradebookResponse,
  GradebookTaskItem,
  GradebookStudentItem,
  StudentGrades,
  GradingFormula,
  ClassStatus
} from '../models/teacher.model';

@Injectable({
  providedIn: 'root'
})
export class TeacherClassService {
  private http = inject(HttpClient);
  
  // States
  private classesState = signal<TeacherCourseItem[]>([]);
  private isLoadingState = signal<boolean>(false);
  
  private currentDetailState = signal<TeacherCourseDetail | null>(null);
  private currentGradebookState = signal<GradebookResponse | null>(null);

  // Getter signals
  classes = this.classesState.asReadonly();
  isLoading = this.isLoadingState.asReadonly();
  currentDetail = this.currentDetailState.asReadonly();
  currentGradebook = this.currentGradebookState.asReadonly();

  constructor() {
    this.loadTeacherClasses().subscribe();
  }

  private normalizeCourseItem(item: any): TeacherCourseItem {
    return {
      id: item.id || item._id,
      code: item.code,
      name: item.name,
      student_total: item.student_total ?? item.studentTotal ?? 0,
      status: item.status,
      is_grade_locked: item.is_grade_locked ?? item.isGradeLocked ?? false,
      allow_practice_submission: item.allow_practice_submission ?? item.allowPracticeSubmission ?? true,
      allow_exam_submission: item.allow_exam_submission ?? item.allowExamSubmission ?? true,
      start_date: item.start_date ?? item.startDate,
      end_date: item.end_date ?? item.endDate,
      exam_date: item.exam_date ?? item.examDate
    };
  }

  private normalizeCourseDetail(item: any): TeacherCourseDetail {
    const base = this.normalizeCourseItem(item);
    const formula = item.grading_formula || item.gradingFormula || item.formula || {};
    return {
      ...base,
      desc: item.desc,
      teacher_id: item.teacher_id || item.teacherId,
      teacher_name: item.teacher_name || item.teacherName,
      grade_locked_at: item.grade_locked_at || item.gradeLockedAt,
      grading_formula: {
        attendance_weight: formula.attendance_weight ?? formula.attendanceWeight ?? 0.2,
        process_weight: formula.process_weight ?? formula.processWeight ?? formula.practice_weight ?? formula.practiceWeight ?? 0.3,
        exam_weight: formula.exam_weight ?? formula.examWeight ?? 0.5,
        practice_tasks_count: formula.practice_tasks_count ?? formula.practiceTasksCount
      },
      total_weeks: item.total_weeks ?? item.totalWeeks ?? 0,
      total_tasks: item.total_tasks ?? item.totalTasks ?? 0
    };
  }

  private normalizeGradebook(data: any): GradebookResponse {
    if (!data) return null as any;
    const rawTasks = data.task_list || data.taskList || [];
    const task_list: GradebookTaskItem[] = rawTasks.map((t: any) => ({
      id: t.id || t._id,
      title: t.title,
      category: t.category
    }));

    const rawFormula = data.formula || data.grading_formula || data.gradingFormula || {};
    const formula: GradingFormula = {
      attendance_weight: rawFormula.attendance_weight ?? rawFormula.attendanceWeight ?? 0.2,
      process_weight: rawFormula.process_weight ?? rawFormula.processWeight ?? rawFormula.practice_weight ?? rawFormula.practiceWeight ?? 0.3,
      exam_weight: rawFormula.exam_weight ?? rawFormula.examWeight ?? 0.5,
      practice_tasks_count: rawFormula.practice_tasks_count ?? rawFormula.practiceTasksCount
    };

    const rawStudents = data.students || [];
    const students: GradebookStudentItem[] = rawStudents.map((s: any) => {
      const g = s.grades || {};
      const grades: StudentGrades = {
        attendance_score: g.attendance_score ?? g.attendanceScore,
        process_score: g.process_score ?? g.processScore,
        exam_score: g.exam_score ?? g.examScore,
        final_score: g.final_score ?? g.finalScore,
        letter_grade: g.letter_grade ?? g.letterGrade,
        is_passed: g.is_passed ?? g.isPassed
      };

      return {
        enrollment_id: s.enrollment_id || s.enrollmentId || s.id || s._id,
        user_id: s.user_id || s.userId,
        student_code: s.student_code || s.studentCode,
        student_name: s.student_name || s.studentName,
        student_email: s.student_email || s.studentEmail,
        gender: s.gender || s.studentGender,
        status: s.status || 'active',
        progress_percent: s.progress_percent ?? s.progressPercent ?? 0,
        task_scores: s.task_scores || s.taskScores || {},
        grades,
        note: s.note
      };
    });

    return {
      course_id: data.course_id || data.courseId,
      is_grade_locked: data.is_grade_locked ?? data.isGradeLocked ?? false,
      formula,
      task_list,
      students
    };
  }

  /**
   * Lấy danh sách lớp học phần của giảng viên
   */
  loadTeacherClasses(): Observable<TeacherCourseItem[]> {
    this.isLoadingState.set(true);
    return this.http.get<ApiResponse<any[]>>(`${environment.apiUrl}/teacher/courses`).pipe(
      map((res) => (res?.data || []).map(item => this.normalizeCourseItem(item))),
      tap((items) => {
        this.classesState.set(items);
        this.isLoadingState.set(false);
      }),
      catchError(() => {
        this.isLoadingState.set(false);
        this.classesState.set([]);
        return of([]);
      })
    );
  }

  /**
   * Lấy chi tiết lớp học phần
   */
  loadCourseDetail(courseId: string): Observable<TeacherCourseDetail | null> {
    return this.http.get<ApiResponse<any>>(`${environment.apiUrl}/teacher/courses/${courseId}`).pipe(
      map(res => res?.data ? this.normalizeCourseDetail(res.data) : null),
      tap(detail => this.currentDetailState.set(detail)),
      catchError(() => of(null))
    );
  }

  /**
   * Lấy sổ điểm của lớp
   */
  loadGradebook(courseId: string): Observable<GradebookResponse | null> {
    return this.http.get<ApiResponse<any>>(`${environment.apiUrl}/teacher/courses/${courseId}/gradebook`).pipe(
      map(res => res?.data ? this.normalizeGradebook(res.data) : null),
      tap(gradebook => this.currentGradebookState.set(gradebook)),
      catchError(() => of(null))
    );
  }

  /**
   * Khóa / Mở nộp bài cho toàn bộ lớp
   */
  toggleSubmissionLock(courseId: string, allowPractice: boolean, allowExam: boolean): Observable<any> {
    return this.http.patch(`${environment.apiUrl}/teacher/courses/${courseId}/submission-lock`, {
      allow_practice_submission: allowPractice,
      allow_exam_submission: allowExam
    });
  }

  /**
   * Lưu điểm thủ công (batch)
   */
  batchUpdateGrades(courseId: string, updates: any[]): Observable<any> {
    return this.http.put(`${environment.apiUrl}/teacher/courses/${courseId}/grades`, { updates });
  }

  /**
   * Chốt sổ điểm
   */
  finalizeClassGrades(courseId: string, finalRemarks?: string): Observable<any> {
    return this.http.post(`${environment.apiUrl}/teacher/courses/${courseId}/finalize-grades`, {
      confirm: true,
      final_remarks: finalRemarks,
      force: false
    });
  }

  /**
   * Mở khóa sổ điểm
   */
  reopenClassGrades(courseId: string, reason: string = 'Giáo viên yêu cầu điều chỉnh điểm'): Observable<any> {
    return this.http.post(`${environment.apiUrl}/teacher/courses/${courseId}/unlock-grades`, { reason });
  }
}
