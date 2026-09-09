import { Component, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import {
  LucideBookOpen,
  LucideGraduationCap,
  LucideAward,
  LucideCalendar,
  LucideChevronRight,
  LucidePlay,
  LucideBell,
  LucideTrendingUp,
  LucideSparkles,
  LucideFileText,
  LucideMapPin,
  LucideCheckCheck,
  LucideAlertCircle,
  LucideInfo
} from '@lucide/angular';
import { NotificationService } from '@core/services/notification.service';
import {
  StudentSummary,
  ActiveCourseSummary,
  ScheduleItem,
  AssignmentTask
} from './models/dashboard.model';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [
    CommonModule,
    LucideBookOpen,
    LucideGraduationCap,
    LucideAward,
    LucideCalendar,
    LucideChevronRight,
    LucidePlay,
    LucideBell,
    LucideTrendingUp,
    LucideSparkles,
    LucideFileText,
    LucideMapPin,
    LucideCheckCheck,
    LucideAlertCircle,
    LucideInfo
  ],
  templateUrl: './home.component.html',
  styleUrl: './home.component.scss'
})
export class HomeComponent {
  private router = inject(Router);
  notificationService = inject(NotificationService);

  // Student summary info
  student = signal<StudentSummary>({
    fullName: 'Nguyễn Văn A',
    studentId: 'SV2026001',
    avatarUrl: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=250&auto=format&fit=crop&q=80',
    faculty: 'Công nghệ Thông tin & Thị giác máy tính',
    major: 'Kỹ thuật Phần mềm & AI',
    classCode: 'CNTT2-K17',
    semester: 'Học kỳ 1 (2024 - 2025)',
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

  // Active courses for "Tiếp tục học tập"
  activeCourses = signal<ActiveCourseSummary[]>([
    {
      id: '1',
      title: 'Thị giác máy tính nâng cao (Advanced Computer Vision)',
      code: 'IT4020',
      instructor: 'TS. Lê Hoàng Sơn',
      progress: 75,
      completedLessons: 9,
      totalLessons: 12,
      currentLesson: 'Tuần 10: Theo dõi đối tượng và nhận diện chuyển động',
      coverImage: 'https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=500&auto=format&fit=crop&q=80',
      category: 'Chuyên ngành'
    },
    {
      id: '2',
      title: 'Học sâu & Ứng dụng AI trong Thị giác (Deep Learning)',
      code: 'IT4030',
      instructor: 'PGS. TS. Trần Minh Tuấn',
      progress: 60,
      completedLessons: 6,
      totalLessons: 10,
      currentLesson: 'Tuần 7: Mạng nơ-ron tích chập (CNN) và ResNet',
      coverImage: 'https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=500&auto=format&fit=crop&q=80',
      category: 'Chuyên ngành'
    },
    {
      id: '3',
      title: 'Xử lý ảnh số & Phân tích dữ liệu đa phương tiện',
      code: 'IT3010',
      instructor: 'ThS. Nguyễn Thu Hà',
      progress: 90,
      completedLessons: 9,
      totalLessons: 10,
      currentLesson: 'Tuần 9: Phân vùng ảnh và phép biến đổi Fourier',
      coverImage: 'https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=500&auto=format&fit=crop&q=80',
      category: 'Cơ sở ngành'
    }
  ]);

  // Today's schedule
  todaySchedule = signal<ScheduleItem[]>([
    {
      id: 'sch-1',
      subjectName: 'Thị giác máy tính nâng cao (Thực hành Lab)',
      subjectCode: 'IT4020',
      room: 'Lab AI - P.502 Nhà A1',
      timeSlot: '07:30 - 09:30',
      period: 'Tiết 1 - 3',
      instructor: 'TS. Lê Hoàng Sơn',
      status: 'completed'
    },
    {
      id: 'sch-2',
      subjectName: 'Học sâu & Ứng dụng AI trong Thị giác (Lý thuyết)',
      subjectCode: 'IT4030',
      room: 'Giảng đường B3 - P.204',
      timeSlot: '13:00 - 15:00',
      period: 'Tiết 7 - 9',
      instructor: 'PGS. TS. Trần Minh Tuấn',
      status: 'ongoing'
    },
    {
      id: 'sch-3',
      subjectName: 'Hội thảo Đánh giá Thể chất & Động tác qua AI (OptiVisionLab)',
      subjectCode: 'SEM-AI',
      room: 'Hội trường Tầng 3 - SICT',
      timeSlot: '15:30 - 17:00',
      period: 'Tiết 10 - 11',
      instructor: 'Hội đồng Khoa học SICT',
      status: 'upcoming'
    }
  ]);

  // Upcoming assignment tasks
  upcomingTasks = signal<AssignmentTask[]>([
    {
      id: 'task-1',
      title: 'Báo cáo thực hành Tuần 10: Theo dõi đối tượng & Nhận diện chuyển động',
      courseName: 'Thị giác máy tính nâng cao (IT4020)',
      dueDate: 'Hôm nay, 23:59',
      status: 'urgent'
    },
    {
      id: 'task-2',
      title: 'Bài tập lớn giữa kỳ: Xây dựng mô hình phân loại ảnh với ResNet',
      courseName: 'Học sâu & Ứng dụng AI (IT4030)',
      dueDate: '15/10/2024 - 23:59',
      status: 'pending'
    },
    {
      id: 'task-3',
      title: 'Trắc nghiệm chương 4: Phép biến đổi Fourier & Lọc không gian',
      courseName: 'Xử lý ảnh số (IT3010)',
      dueDate: 'Đã hoàn thành',
      status: 'submitted',
      score: 10
    }
  ]);

  // Computed latest 3 notifications
  recentNotifications = computed(() => {
    return this.notificationService.notifications().slice(0, 3);
  });

  navigateToCourse(courseId: string): void {
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
