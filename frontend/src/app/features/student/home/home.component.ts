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
  LucideBookOpen,
  LucideArrowRight,
  LucideUser,
  LucideCheckCircle2
} from '@lucide/angular';
import { NotificationService } from '@core/services/notification.service';
import { AuthService } from '@core/services/auth.service';
import { environment } from '../../../../environments/environment';
import { ApiResponse } from '../../../core/models/auth.model';
import {
  StudentSummary,
  ScheduleItem,
  ActiveCourseSummary
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
    LucideBookOpen,
    LucideArrowRight,
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
      semester: 'Học kỳ hiện tại',
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

  // Danh sách các môn học / lớp học phần đang học
  enrolledCourses = signal<ActiveCourseSummary[]>([]);

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

    // Tải các môn học thực tế đã ghi danh của sinh viên
    this.http.get<ApiResponse<any>>(`${environment.apiUrl}/enrollments/my-courses`).subscribe({
      next: (res) => {
        const items = res?.data?.items || (Array.isArray(res?.data) ? res.data : []);
        if (items.length > 0) {
          // 1. Map danh sách khóa học kèm tiến độ
          const courseList: ActiveCourseSummary[] = items.map((item: any) => {
            const courseId = item.courseId || item.id || '';
            const courseName = item.courseName || item.name || 'Giáo dục Thể chất';
            const isBadminton = courseName.toLowerCase().includes('cầu lông') ||
              courseName.toLowerCase().includes('badminton') ||
              courseName.toLowerCase().includes('pickleball');
            const classCode = item.courseCode || item.code || (courseId.length > 8 ? courseId.substring(0, 10).toUpperCase() : courseId);
            const score = item.grades?.finalScore ?? item.grades?.processScore ?? item.grades?.attendanceScore;
            return {
              id: courseId,
              title: courseName,
              code: classCode,
              instructor: item.teacherName || 'Giảng viên phụ trách',
              progress: Math.round(item.progressPercent || 0),
              iconType: isBadminton ? 'pickleball' : 'chay',
              finalScore: score !== null && score !== undefined ? score : undefined,
              examDate: item.examDate ? new Date(item.examDate).toLocaleDateString('vi-VN') : undefined
            };
          });
          this.enrolledCourses.set(courseList);

          // 2. Map lịch học
          const mapped: ScheduleItem[] = items.map((item: any, idx: number) => ({
            id: item.id || item.courseId || `sch-${idx}`,
            dayOfWeek: idx % 2 === 0 ? 'T3' : 'T5',
            date: 'Thứ Ba & Thứ Năm hàng tuần',
            sessionPeriod: 'Buổi sáng - Tiết 1,2,3',
            subjectName: item.courseName || item.name || 'Môn học Giáo dục Thể chất',
            instructor: item.teacherName || 'Giảng viên phụ trách',
            room: 'Sân Thể chất HaUI'
          }));
          this.todaySchedule.set(mapped);
        } else {
          this.enrolledCourses.set([]);
          this.todaySchedule.set([]);
        }
      },
      error: () => {
        this.enrolledCourses.set([]);
        this.todaySchedule.set([]);
      }
    });
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

  navigateToCourse(courseId: string): void {
    this.router.navigate(['/student/courses', courseId]);
  }

  navigateToAllCourses(): void {
    this.router.navigate(['/student/courses']);
  }

  navigateToNotifications(): void {
    this.router.navigate(['/student/notifications']);
  }
}

