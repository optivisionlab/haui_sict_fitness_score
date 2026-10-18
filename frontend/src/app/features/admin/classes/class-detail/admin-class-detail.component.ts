import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import {
  LucideBookOpen,
  LucideArrowLeft,
  LucideUserPlus,
  LucideUsers,
  LucideTrash2,
  LucideGraduationCap,
  LucideUserCheck,
  LucideTrophy,
  LucideSearch,
  LucideCheckCircle2,
  LucideAlertCircle,
  LucideX
} from '@lucide/angular';
import { AdminService, Course, Enrollment } from '@core/services/admin.service';
import { User } from '@core/models/auth.model';
import { ToastService } from '@core/services/toast.service';

@Component({
  selector: 'app-admin-class-detail',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    LucideBookOpen,
    LucideArrowLeft,
    LucideUserPlus,
    LucideUsers,
    LucideTrash2,
    LucideGraduationCap,
    LucideUserCheck,
    LucideTrophy,
    LucideSearch,
    LucideCheckCircle2,
    LucideAlertCircle,
    LucideX
  ],
  templateUrl: './admin-class-detail.component.html',
  styleUrl: './admin-class-detail.component.scss'
})
export class AdminClassDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private adminService = inject(AdminService);
  private toastService = inject(ToastService);

  courseId = signal<string>('');
  course = signal<Course | null>(null);
  enrollments = signal<Enrollment[]>([]);
  allStudents = signal<User[]>([]);
  isLoading = signal<boolean>(true);
  searchTerm = signal<string>('');

  // Enroll modal
  showEnrollModal = signal<boolean>(false);
  selectedStudentId = signal<string>('');
  isEnrolling = signal<boolean>(false);
  modalStudentSearch = signal<string>('');

  // Delete modal
  showRemoveModal = signal<boolean>(false);
  enrollmentToRemove = signal<Enrollment | null>(null);

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.courseId.set(id);
      this.loadCourseData();
    } else {
      this.router.navigate(['/admin/classes']);
    }
  }

  loadCourseData(): void {
    this.isLoading.set(true);

    this.adminService.getCourseDetail(this.courseId()).subscribe({
      next: (c) => {
        this.course.set(c);
      },
      error: () => {
        this.toastService.error('Không tìm thấy thông tin lớp học phần');
      }
    });

    this.adminService.getCourseEnrollments(this.courseId()).subscribe({
      next: (res) => {
        this.enrollments.set(res.items || []);
        this.isLoading.set(false);
      },
      error: () => {
        this.isLoading.set(false);
      }
    });

    // Tải danh sách tất cả sinh viên để phục vụ thêm vào lớp
    this.adminService.getUsers('student', 1, 200).subscribe({
      next: (res) => {
        this.allStudents.set(res.items || []);
      }
    });
  }

  get filteredEnrollments(): Enrollment[] {
    const term = this.searchTerm().trim().toLowerCase();
    if (!term) return this.enrollments();
    return this.enrollments().filter(e =>
      (e.user_name && e.user_name.toLowerCase().includes(term)) ||
      (e.student_code && e.student_code.toLowerCase().includes(term))
    );
  }

  // Danh sách sinh viên chưa có trong lớp này
  get availableStudents(): User[] {
    const enrolledUserIds = new Set(this.enrollments().map(e => e.user_id));
    const term = this.modalStudentSearch().trim().toLowerCase();

    return this.allStudents().filter(s => {
      if (enrolledUserIds.has(s.id)) return false;
      if (!term) return true;
      return (
        (s.name && s.name.toLowerCase().includes(term)) ||
        (s.user_code && s.user_code.toLowerCase().includes(term)) ||
        (s.email && s.email.toLowerCase().includes(term))
      );
    });
  }

  openEnrollModal(): void {
    this.selectedStudentId.set('');
    this.modalStudentSearch.set('');
    this.showEnrollModal.set(true);
  }

  closeEnrollModal(): void {
    this.showEnrollModal.set(false);
  }

  onExecuteEnroll(): void {
    const studentId = this.selectedStudentId();
    if (!studentId) {
      this.toastService.warning('Vui lòng chọn một sinh viên để ghi danh');
      return;
    }

    this.isEnrolling.set(true);
    this.adminService.enrollStudent(this.courseId(), studentId).subscribe({
      next: () => {
        this.isEnrolling.set(false);
        this.toastService.success('Đã ghi danh sinh viên vào lớp học phần!');
        this.closeEnrollModal();
        this.loadCourseData();
      },
      error: (err) => {
        this.isEnrolling.set(false);
        this.toastService.error('Ghi danh thất bại: ' + (err.message || 'Lỗi hệ thống'));
      }
    });
  }

  confirmRemove(enrollment: Enrollment): void {
    this.enrollmentToRemove.set(enrollment);
    this.showRemoveModal.set(true);
  }

  cancelRemove(): void {
    this.showRemoveModal.set(false);
    this.enrollmentToRemove.set(null);
  }

  onExecuteRemove(): void {
    const en = this.enrollmentToRemove();
    if (!en) return;

    this.adminService.removeEnrollment(en.id).subscribe({
      next: () => {
        this.toastService.success(`Đã gỡ sinh viên ${en.user_name} khỏi lớp`);
        this.cancelRemove();
        this.loadCourseData();
      },
      error: (err) => {
        this.toastService.error('Gỡ sinh viên thất bại: ' + (err.message || 'Lỗi server'));
      }
    });
  }
}
