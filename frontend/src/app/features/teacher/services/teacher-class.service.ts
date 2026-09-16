import { Injectable, signal, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap, map, catchError, of } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { ApiResponse } from '../../../core/models/auth.model';
import { TeacherClass, ClassStatus, StudentGradeRecord, ClassAssessment } from '../models/teacher.model';
import { INITIAL_TEACHER_CLASSES } from '../models/teacher-mock-data';

@Injectable({
  providedIn: 'root'
})
export class TeacherClassService {
  private http = inject(HttpClient);
  private classesState = signal<TeacherClass[]>([]);
  private isLoadingState = signal<boolean>(false);

  // Getter signals
  classes = this.classesState.asReadonly();
  isLoading = this.isLoadingState.asReadonly();

  constructor() {
    this.loadTeacherClasses().subscribe();
  }

  /**
   * Kéo danh sách lớp học phần của giảng viên từ database qua API /teacher/courses
   */
  loadTeacherClasses(): Observable<TeacherClass[]> {
    this.isLoadingState.set(true);
    return this.http.get<ApiResponse<any[]>>(`${environment.apiUrl}/teacher/courses`).pipe(
      map((res) => {
        const items = res?.data || [];
        if (!items || items.length === 0) {
          return INITIAL_TEACHER_CLASSES;
        }

        return items.map((c: any) => this.mapApiCourseToTeacherClass(c));
      }),
      tap((mapped) => {
        this.classesState.set(mapped);
        this.isLoadingState.set(false);
      }),
      catchError(() => {
        this.isLoadingState.set(false);
        this.classesState.set(INITIAL_TEACHER_CLASSES);
        return of(INITIAL_TEACHER_CLASSES);
      })
    );
  }

  /**
   * Tải chi tiết sổ điểm của lớp từ /teacher/courses/{id}/gradebook
   */
  loadGradebook(classId: string): Observable<TeacherClass | null> {
    return this.http.get<ApiResponse<any>>(`${environment.apiUrl}/teacher/courses/${classId}/gradebook`).pipe(
      map((res) => {
        const data = res?.data;
        if (!data) return null;

        const current = this.getClassById(classId);
        if (!current) return null;

        // Map task list to assessments
        const assessments: ClassAssessment[] = (data.taskList || []).map((t: any, idx: number) => ({
          id: t.id,
          name: t.title,
          type: t.category === 'exam' ? 'final' : (`tx${idx + 1}` as any),
          weight: t.category === 'exam' ? 50 : 25,
          gradingMethod: 'Chấm điểm bằng AI',
          timeLimit: '60 phút',
          openTime: '2026-09-01 08:00',
          closeTime: '2026-12-01 23:59',
          submittedCount: (data.students || []).filter((s: any) => s.taskScores && s.taskScores[t.id] !== undefined).length,
          totalCount: (data.students || []).length,
          isLocked: !current.isSubmissionLocked,
          status: 'open'
        }));

        // Map students from database
        const students: StudentGradeRecord[] = (data.students || []).map((s: any) => {
          const taskKeys = Object.keys(s.taskScores || {});
          const t1 = taskKeys.length > 0 ? s.taskScores[taskKeys[0]] : null;
          const t2 = taskKeys.length > 1 ? s.taskScores[taskKeys[1]] : null;

          return {
            id: s.userId || s.studentCode,
            studentCode: s.studentCode || '',
            fullName: s.studentName || '',
            majorClass: 'D17CNPM1',
            tx1Score: s.grades?.attendanceScore ?? t1 ?? null,
            tx2Score: s.grades?.processScore ?? t2 ?? null,
            midtermScore: null,
            finalScore: s.grades?.examScore ?? null,
            finalAvgScore: s.grades?.finalScore ?? null,
            letterGrade: s.grades?.letterGrade ?? null,
            resultStatus: s.grades?.isPassed === true ? 'pass' : (s.grades?.isPassed === false ? 'fail' : 'pending'),
            avatar: s.gender === 'Nữ'
              ? 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=150&auto=format&fit=crop&q=80'
              : 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80'
          };
        });

        const updatedClass: TeacherClass = {
          ...current,
          studentCount: students.length,
          assessments: assessments.length > 0 ? assessments : current.assessments,
          students: students.length > 0 ? students : current.students
        };

        this.classesState.update((classes) =>
          classes.map((c) => (c.id === classId ? updatedClass : c))
        );

        return updatedClass;
      }),
      catchError(() => of(this.getClassById(classId) || null))
    );
  }

  private mapApiCourseToTeacherClass(c: any): TeacherClass {
    const isBadminton = c.name?.toLowerCase().includes('cầu lông') || c.name?.toLowerCase().includes('badminton');
    const isRunning = c.name?.toLowerCase().includes('điền kinh') || c.name?.toLowerCase().includes('chạy');

    return {
      id: c.id,
      code: c.code,
      name: c.name,
      semester: 'Học kỳ 1 - 2026-2027',
      schedule: 'Thứ 3 & Thứ 5, Tiết 1-3',
      location: 'Sân Giáo dục Thể chất HaUI',
      studentCount: c.studentTotal ?? 0,
      maxStudents: 40,
      progressSessions: 6,
      totalSessions: 15,
      status: c.status === 'completed' ? 'finalized' : 'active',
      iconType: isBadminton ? 'pickleball' : (isRunning ? 'chay' : 'fitness'),
      teacherName: 'ThS. Trần Thị Bình',
      teacherCode: 'GV001',
      isPracticeLocked: !c.allowPracticeSubmission,
      isSubmissionLocked: !c.allowExamSubmission,
      isFinalized: c.isGradeLocked ?? false,
      assessments: [],
      students: []
    };
  }

  getClassById(id: string): TeacherClass | undefined {
    return this.classesState().find(c => c.id === id);
  }

  togglePracticeLock(classId: string): boolean {
    let newState = false;
    this.classesState.update(classes =>
      classes.map(c => {
        if (c.id === classId) {
          newState = !c.isPracticeLocked;
          return { ...c, isPracticeLocked: newState };
        }
        return c;
      })
    );
    return newState;
  }

  toggleSubmissionLock(classId: string): boolean {
    let newState = false;
    this.classesState.update(classes =>
      classes.map(c => {
        if (c.id === classId) {
          newState = !c.isSubmissionLocked;
          // Also sync assessments locks
          const updatedAssessments = c.assessments.map(a => ({
            ...a,
            isLocked: newState
          }));
          return { ...c, isSubmissionLocked: newState, assessments: updatedAssessments };
        }
        return c;
      })
    );
    return newState;
  }

  toggleAssessmentLock(classId: string, assessmentId: string): boolean {
    let newLock = false;
    this.classesState.update(classes =>
      classes.map(c => {
        if (c.id === classId) {
          const assessments = c.assessments.map(a => {
            if (a.id === assessmentId) {
              newLock = !a.isLocked;
              return { ...a, isLocked: newLock };
            }
            return a;
          });
          return { ...c, assessments };
        }
        return c;
      })
    );
    return newLock;
  }

  finalizeClassGrades(classId: string, teacherName: string): boolean {
    this.classesState.update(classes =>
      classes.map(c => {
        if (c.id === classId) {
          const now = new Date();
          const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')} ngày ${now.getDate().toString().padStart(2, '0')}/${(now.getMonth() + 1).toString().padStart(2, '0')}/${now.getFullYear()}`;
          return {
            ...c,
            status: 'finalized' as ClassStatus,
            isFinalized: true,
            isPracticeLocked: true,
            isSubmissionLocked: true,
            finalizedAt: timeStr,
            finalizedBy: teacherName
          };
        }
        return c;
      })
    );
    return true;
  }

  reopenClassGrades(classId: string): void {
    this.classesState.update(classes =>
      classes.map(c => {
        if (c.id === classId) {
          return {
            ...c,
            status: 'active' as ClassStatus,
            isFinalized: false
          };
        }
        return c;
      })
    );
  }

  updateStudentScore(
    classId: string,
    studentId: string,
    field: 'tx1Score' | 'tx2Score' | 'midtermScore' | 'finalScore',
    value: number | null
  ): void {
    this.classesState.update(classes =>
      classes.map(c => {
        if (c.id === classId) {
          const students = c.students.map(s => {
            if (s.id === studentId) {
              const updated = { ...s, [field]: value };
              // Recalculate average
              const scores = [updated.tx1Score, updated.tx2Score, updated.midtermScore, updated.finalScore].filter(
                (v): v is number => v !== null
              );
              let avg: number | null = null;
              if (scores.length > 0) {
                // Calculation: TX1 (15%) + TX2 (15%) + Midterm (30%) + Final (40%)
                const wTx1 = (updated.tx1Score ?? 0) * 0.15;
                const wTx2 = (updated.tx2Score ?? 0) * 0.15;
                const wMid = (updated.midtermScore ?? 0) * 0.3;
                const wFin = (updated.finalScore ?? 0) * 0.4;
                avg = Math.round((wTx1 + wTx2 + wMid + wFin) * 10) / 10;
              }
              updated.finalAvgScore = avg;
              if (avg !== null) {
                if (avg >= 8.5) updated.letterGrade = 'A';
                else if (avg >= 8.0) updated.letterGrade = 'B+';
                else if (avg >= 7.0) updated.letterGrade = 'B';
                else if (avg >= 6.5) updated.letterGrade = 'C+';
                else if (avg >= 5.5) updated.letterGrade = 'C';
                else if (avg >= 5.0) updated.letterGrade = 'D+';
                else if (avg >= 4.0) updated.letterGrade = 'D';
                else updated.letterGrade = 'F';

                updated.resultStatus = avg >= 5.0 ? 'pass' : 'fail';
              }
              return updated;
            }
            return s;
          });
          return { ...c, students };
        }
        return c;
      })
    );
  }
}
