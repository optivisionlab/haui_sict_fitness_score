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
          const mappedCourses = items.map((item: any, idx: number) => {
            const code = item.courseCode || item.code || `GDTC0${idx + 1}`;
            const name = item.courseName || item.name || 'Giáo dục thể chất';
            const teacher = item.teacherName || item.teacher || 'Giảng viên phụ trách';
            const progress = typeof item.progress === 'number' ? item.progress : (idx === 0 ? 65 : 40);
            const iconType = (item.sportCode?.toLowerCase().includes('chay') || name.toLowerCase().includes('chạy')) ? 'chay' : 'pickleball';
            return {
              id: item.courseId || item.id || `c-${idx}`,
              name,
              code,
              teacher,
              progress,
              iconType
            };
          });
          this.enrolledCourses.set(mappedCourses);

          const mapped: ScheduleItem[] = items.map((item: any, idx: number) => ({
            id: item.id || item.courseId || `sch-${idx}`,
            dayOfWeek: idx % 2 === 0 ? 'T3' : 'T5',
            date: 'Thứ Ba & Thứ Năm hàng tuần',
            sessionPeriod: 'Buổi sáng - Tiết 1,2,3',
            subjectName: item.courseName || item.name || 'Môn học Giáo dục Thể chất',
            instructor: item.teacherName || 'Giảng viên phụ trách',
            room: 'Sân Thể chất'
          }));
          this.todaySchedule.set(mapped);
        } else {
          // Khóa học mặc định mẫu nếu API chưa có dữ liệu để trải nghiệm luôn trực quan
          this.enrolledCourses.set([
            {
              id: 'c-pickleball',
              name: 'Pickleball - Kỹ thuật cơ bản & Nâng cao',
              code: 'LHP-GDTC204-01',
              teacher: 'ThS. Nguyễn Văn A',
              progress: 60,
              iconType: 'pickleball'
            }
          ]);
          this.todaySchedule.set([]);
        }
      },
      error: () => {
        this.enrolledCourses.set([
          {
            id: 'c-pickleball',
            name: 'Pickleball - Kỹ thuật cơ bản & Nâng cao',
            code: 'LHP-GDTC204-01',
            teacher: 'ThS. Nguyễn Văn A',
            progress: 60,
            iconType: 'pickleball'
          }
        ]);
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

