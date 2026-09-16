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
  LucideInfo
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
    LucideInfo
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
    return {
      fullName: user?.name || 'Sinh viên',
      studentId: user?.userCode || user?.user_code || 'SV2021001',
      avatarUrl: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=250&auto=format&fit=crop&q=80',
      faculty: 'Giáo dục Thể chất',
      major: 'Thể thao & Thể chất',
      classCode: 'CNTT2-K17',
      semester: 'Học kỳ 1 (2026 - 2027)',
      gpa: 3.68,
      creditsEarned: 128,
      trainingScore: 90
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
    // Tải các môn học thực tế đã ghi danh của sinh viên
    this.http.get<ApiResponse<any>>(`${environment.apiUrl}/enrollments/my-courses`).subscribe({
      next: (res) => {
        const items = res?.data?.items || [];
        if (items.length > 0) {
          const mapped: ScheduleItem[] = items.map((item: any, idx: number) => ({
            id: item.id || `sch-${idx}`,
            dayOfWeek: idx % 2 === 0 ? 'T3' : 'T5',
            date: 'Thứ Ba hàng tuần',
            sessionPeriod: 'Buổi sáng - Tiết 1,2,3',
            subjectName: item.courseName || 'Môn học Giáo dục Thể chất',
            instructor: item.teacherName || 'Giảng viên phụ trách',
            room: 'Sân Giáo dục Thể chất HaUI'
          }));
          this.todaySchedule.set(mapped);
        } else {
          this.todaySchedule.set([
            {
              id: 'sch-default',
              dayOfWeek: 'T3',
              date: 'Lịch học',
              sessionPeriod: 'Buổi sáng - Tiết 1,2,3',
              subjectName: 'Giáo dục Thể chất 1',
              instructor: 'ThS. Trần Thị Bình',
              room: 'Sân thể chất'
            }
          ]);
        }
      },
      error: () => {}
    });
  }

  // Computed latest notifications (show up to 4 recent notifications)
  recentNotifications = computed(() => {
    return this.notificationService.notifications().slice(0, 4);
  });

  navigateToNotifications(): void {
    this.router.navigate(['/student/notifications']);
  }
}

