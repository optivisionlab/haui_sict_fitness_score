import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import {
  LucideGraduationCap,
  LucideCalendar,
  LucideChevronRight,
  LucideBell,
  LucideAlertCircle,
  LucideInfo,
  LucideDumbbell,
  LucideFootprints,
  LucideUser
} from '@lucide/angular';
import { NotificationService } from '@core/services/notification.service';
import { AuthService } from '@core/services/auth.service';
import { environment } from '../../../../environments/environment';
import { ApiResponse } from '../../../core/models/auth.model';
import {
  StudentSummary,
  ScheduleItem
} from './models/dashboard.model';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [
    CommonModule,
    LucideGraduationCap,
    LucideCalendar,
    LucideChevronRight,
    LucideBell,
    LucideAlertCircle,
    LucideInfo,
    LucideDumbbell,
    LucideFootprints,
    LucideUser
  ],
  templateUrl: './home.component.html',
  styleUrl: './home.component.scss'
})
export class HomeComponent implements OnInit {
  private router = inject(Router);
  private http = inject(HttpClient);
  private authService = inject(AuthService);
  notificationService = inject(NotificationService);

  // Student summary info
  student = signal<StudentSummary>(this.getInitialStudent());

  // Enrolled courses with progress
  enrolledCourses = signal<any[]>([]);
  loadError = signal(false);

  private getInitialStudent(): StudentSummary {
    const user = this.authService.currentUser();
    const name = user?.name || 'Sinh viên';
    return {
      fullName: name,
      studentId: user?.userCode || user?.user_code || 'Chưa cập nhật',
      avatarUrl: `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&background=0284c7&color=fff&bold=true`,
      faculty: 'Chưa cập nhật',
      major: 'Chưa cập nhật',
      classCode: 'Chưa cập nhật',
      semester: '',
      gpa: 0,
      creditsEarned: 0,
      trainingScore: 0
    };
  }

  // Current greeting based on time of day
  greeting = computed(() => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Chào buổi sáng';
    if (hour < 18) return 'Chào buổi chiều';
    return 'Chào buổi tối';
  });

  // Today's schedule / Weekly timeline
  todaySchedule = signal<ScheduleItem[]>([]);

  ngOnInit(): void {
    // Tải thông báo từ backend
    this.notificationService.loadNotifications();

    // Cập nhật thông tin sinh viên từ auth service
    const user = this.authService.currentUser();
    if (user) {
      this.updateStudentInfo(user);
    } else {
      this.authService.fetchCurrentUser().subscribe({
        next: (u) => this.updateStudentInfo(u),
        error: () => {}
      });
    }

    // Tải các môn học thực tế đã ghi danh của sinh viên (kèm thông tin lớp học phần)
    this.http.get<ApiResponse<any>>(`${environment.apiUrl}/enrollments/my-courses`).subscribe({
      next: (res) => {
        const items: any[] = res?.data?.items || (Array.isArray(res?.data) ? res.data : []);

        this.enrolledCourses.set(items.map((item: any) => {
          const name = item.courseName || '';
          const isRunning = (item.sportCode || '').toLowerCase().includes('chay')
            || /chạy|điền kinh/i.test(name);
          return {
            id: item.courseId,
            name,
            code: item.courseCode || '',
            teacher: item.teacherName || '',
            progress: Math.round(item.progressPercent || 0),
            iconType: isRunning ? 'chay' : 'pickleball'
          };
        }));

        // Học kỳ lấy từ lớp học phần đầu tiên có khai báo học kỳ
        const semester = items.find((i: any) => i.semesterName)?.semesterName;
        if (semester) {
          this.student.update((s) => ({ ...s, semester }));
        }

        // Lịch học: mỗi buổi học cố định trong tuần của từng lớp, sắp xếp theo thứ
        const sessions: (ScheduleItem & { sortKey: number })[] = [];
        items.forEach((item: any) => {
          (item.schedule || []).forEach((sess: any, idx: number) => {
            sessions.push({
              id: `${item.courseId}-${idx}`,
              sortKey: sess.dayOfWeek * 100 + parseInt(sess.periods, 10) || 0,
              dayOfWeek: sess.dayOfWeek === 8 ? 'CN' : `T${sess.dayOfWeek}`,
              date: HomeComponent.DAY_NAMES[sess.dayOfWeek] || '',
              sessionPeriod: `${HomeComponent.sessionOfDay(sess.periods)} · Tiết ${sess.periods}`,
              subjectName: item.courseName || '',
              instructor: item.teacherName || '',
              room: sess.location || ''
            });
          });
        });
        sessions.sort((a, b) => a.sortKey - b.sortKey);
        this.todaySchedule.set(sessions);
      },
      error: () => {
        this.enrolledCourses.set([]);
        this.todaySchedule.set([]);
        this.loadError.set(true);
      }
    });
  }

  private static readonly DAY_NAMES: Record<number, string> = {
    2: 'Thứ Hai', 3: 'Thứ Ba', 4: 'Thứ Tư', 5: 'Thứ Năm', 6: 'Thứ Sáu', 7: 'Thứ Bảy', 8: 'Chủ nhật'
  };

  /** Tiết 1–6: sáng, 7–12: chiều, từ 13: tối. */
  private static sessionOfDay(periods: string): string {
    const first = parseInt(periods, 10);
    if (first >= 13) return 'Buổi tối';
    if (first >= 7) return 'Buổi chiều';
    return 'Buổi sáng';
  }

  private updateStudentInfo(user: any): void {
    if (!user) return;
    const name = user.name || 'Sinh viên';
    this.student.update((s) => ({
      ...s,
      fullName: name,
      studentId: user.userCode || user.user_code || s.studentId,
      avatarUrl: `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&background=0284c7&color=fff&bold=true`
    }));
  }

  // Computed latest notifications (show up to 4 recent notifications)
  recentNotifications = computed(() => {
    return this.notificationService.notifications().slice(0, 4);
  });

  navigateToNotifications(): void {
    this.router.navigate(['/student/notifications']);
  }

  navigateToCourse(courseId?: string): void {
    if (courseId) {
      this.router.navigate(['/student/courses'], { queryParams: { courseId } });
    } else {
      this.router.navigate(['/student/courses']);
    }
  }
}

