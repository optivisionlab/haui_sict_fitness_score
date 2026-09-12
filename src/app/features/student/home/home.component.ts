import { Component, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import {
  LucideBookOpen,
  LucideGraduationCap,
  LucideCalendar,
  LucideChevronRight,
  LucidePlay,
  LucideBell,
  LucideSparkles,
  LucideFileText,
  LucideMapPin,
  LucideAlertCircle,
  LucideInfo
} from '@lucide/angular';
import { NotificationService } from '@core/services/notification.service';
import {
  StudentSummary,
  ActiveCourseSummary,
  ScheduleItem
} from './models/dashboard.model';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [
    CommonModule,
    LucideBookOpen,
    LucideGraduationCap,
    LucideCalendar,
    LucideChevronRight,
    LucidePlay,
    LucideBell,
    LucideSparkles,
    LucideFileText,
    LucideMapPin,
    LucideAlertCircle,
    LucideInfo
  ],
  templateUrl: './home.component.html',
  styleUrl: './home.component.scss'
})
export class HomeComponent {
  private router = inject(Router);
  notificationService = inject(NotificationService);

  // Student summary info (tập trung thông tin sinh viên & lớp học phần)
  student = signal<StudentSummary>({
    fullName: 'Nguyễn Văn A',
    studentId: 'SV2026001',
    avatarUrl: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=250&auto=format&fit=crop&q=80',
    faculty: 'Công nghệ Thông tin & Thị giác máy tính',
    major: 'Kỹ thuật Phần mềm & AI',
    classCode: 'CNTT2-K17',
    semester: 'Học kỳ 1 (2026 - 2027)',
    gpa: 3.68,
    creditsEarned: 128,
    trainingScore: 92
  });

  // Current greeting based on time of day
  greeting = computed(() => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Chào buổi sáng';
    if (hour < 18) return 'Chào buổi chiều';
    return 'Chào buổi tối';
  });

  // Active courses hiển thị trực tiếp môn học và tiến độ
  activeCourses = signal<ActiveCourseSummary[]>([
    {
      id: 'pickleball',
      title: 'Pickleball',
      code: '20261PB0001_TX001',
      instructor: 'Đặng Văn Long',
      progress: 45,
      completedLessons: 1,
      totalLessons: 3,
      currentLesson: 'KT1: Kỹ thuật giao bóng cơ bản',
      coverImage: 'https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=500&auto=format&fit=crop&q=80',
      category: 'Giáo dục Thể chất AI'
    },
    {
      id: 'chay',
      title: 'Chạy (Điền kinh)',
      code: '20261TD0002_TX001',
      instructor: 'Vũ Thị Lan',
      progress: 100,
      completedLessons: 2,
      totalLessons: 2,
      currentLesson: 'KT1: Chạy 400m - Đã hoàn thành',
      coverImage: 'https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=500&auto=format&fit=crop&q=80',
      category: 'Giáo dục Thể chất AI'
    }
  ]);

  // Lịch học hôm nay
  todaySchedule = signal<ScheduleItem[]>([
    {
      id: 'sch-1',
      subjectName: 'Pickleball (Thực hành AI Tracking)',
      subjectCode: '20261PB0001_TX001',
      room: 'Sân Pickleball - Nhà thi đấu Thể thao',
      timeSlot: '07:30 - 09:30',
      period: 'Tiết 1 - 3',
      instructor: 'Đặng Văn Long',
      status: 'ongoing'
    },
    {
      id: 'sch-2',
      subjectName: 'Chạy (Đo vận tốc & Quãng đường AI)',
      subjectCode: '20261TD0002_TX001',
      room: 'Sân vận động Trung tâm',
      timeSlot: '15:30 - 17:00',
      period: 'Tiết 10 - 11',
      instructor: 'Vũ Thị Lan',
      status: 'upcoming'
    }
  ]);

  // Computed latest 3 notifications
  recentNotifications = computed(() => {
    return this.notificationService.notifications().slice(0, 3);
  });

  navigateToCourse(courseId?: string): void {
    this.router.navigate(['/student/courses']);
  }

  navigateToGrades(): void {
    this.router.navigate(['/student/grades']);
  }

  navigateToNotifications(): void {
    this.router.navigate(['/student/notifications']);
  }

  navigateToProfile(): void {
    this.router.navigate(['/student/profile']);
  }
}
