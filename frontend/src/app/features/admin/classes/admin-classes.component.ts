import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import {
  LucideBookOpen,
  LucidePlus,
  LucideSearch,
  LucideEdit3,
  LucideTrash2,
  LucideUsers,
  LucideUserCheck,
  LucideTrophy,
  LucideCheckCircle2,
  LucideAlertCircle,
  LucideX
} from '@lucide/angular';
import { AdminService, Course, CourseCreateRequest, Sport } from '@core/services/admin.service';
import { User } from '@core/models/auth.model';
import { ToastService } from '@core/services/toast.service';

@Component({
  selector: 'app-admin-classes',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    LucideBookOpen,
    LucidePlus,
    LucideSearch,
    LucideEdit3,
    LucideTrash2,
    LucideUsers,
    LucideUserCheck,
    LucideTrophy,
    LucideCheckCircle2,
    LucideAlertCircle,
    LucideX
  ],
  templateUrl: './admin-classes.component.html',
  styleUrl: './admin-classes.component.scss'
})
export class AdminClassesComponent implements OnInit {
  private adminService = inject(AdminService);
  private toastService = inject(ToastService);
  private router = inject(Router);

  courses = signal<Course[]>([]);
  sports = signal<Sport[]>([]);
  teachers = signal<User[]>([]);
  isLoading = signal<boolean>(true);
  searchTerm = signal<string>('');

  // Modal Create/Edit
  showModal = signal<boolean>(false);
  isEditMode = signal<boolean>(false);
  isSubmitting = signal<boolean>(false);
  currentCourseId = signal<string | null>(null);

  courseForm: CourseCreateRequest = {
    code: '',
    name: '',
    desc: '',
    teacher_id: '',
    teacher_name: '',
    sport_id: '',
    sport_name: '',
    key: '2025-2026.1'
  };

  // Delete modal
  showDeleteModal = signal<boolean>(false);
  courseToDelete = signal<Course | null>(null);

  ngOnInit(): void {
    this.loadData();
  }

  loadData(): void {
    this.isLoading.set(true);

    this.adminService.getCourses(1, 100).subscribe({
      next: (res) => {
        this.courses.set(res.items || []);
        this.isLoading.set(false);
      },
      error: (err) => {
        this.isLoading.set(false);
        this.toastService.error('Không thể tải danh sách lớp học: ' + (err.message || 'Lỗi server'));
      }
    });

    this.adminService.getSports(1, 100).subscribe({
      next: (res) => {
        this.sports.set(res.items || []);
      }
    });

    this.adminService.getUsers('teacher', 1, 100).subscribe({
      next: (res) => {
        this.teachers.set(res.items || []);
      }
    });
  }

  get filteredCourses(): Course[] {
    const term = this.searchTerm().trim().toLowerCase();
    if (!term) return this.courses();
    return this.courses().filter(c =>
      c.name.toLowerCase().includes(term) ||
      (c.code && c.code.toLowerCase().includes(term)) ||
      (c.teacher_name && c.teacher_name.toLowerCase().includes(term)) ||
      (c.sport_name && c.sport_name.toLowerCase().includes(term))
    );
  }

  openCreateModal(): void {
    this.isEditMode.set(false);
    this.currentCourseId.set(null);
    const defaultSport = this.sports()[0];
    const defaultTeacher = this.teachers()[0];

    this.courseForm = {
      code: '',
      name: '',
      desc: '',
      teacher_id: defaultTeacher ? defaultTeacher.id : '',
      teacher_name: defaultTeacher ? defaultTeacher.name : '',
      sport_id: defaultSport ? defaultSport.id : '',
      sport_name: defaultSport ? defaultSport.name : '',
      key: '2025-2026.1'
    };
    this.showModal.set(true);
  }

  openEditModal(course: Course): void {
    this.isEditMode.set(true);
    this.currentCourseId.set(course.id);
    this.courseForm = {
      code: course.code || course.key || '',
      name: course.name,
      desc: course.desc || '',
      teacher_id: course.teacher_id,
      teacher_name: course.teacher_name || '',
      sport_id: course.sport_id || '',
      sport_name: course.sport_name || '',
      key: course.key || '2025-2026.1'
    };
    this.showModal.set(true);
  }

  closeModal(): void {
    this.showModal.set(false);
  }

  onSportSelect(sportId: string): void {
    const s = this.sports().find(item => item.id === sportId);
    if (s) {
      this.courseForm.sport_id = s.id;
      this.courseForm.sport_name = s.name;
    }
  }

  onTeacherSelect(teacherId: string): void {
    const t = this.teachers().find(item => item.id === teacherId);
    if (t) {
      this.courseForm.teacher_id = t.id;
      this.courseForm.teacher_name = t.name;
    }
  }

  onSubmitCourse(): void {
    if (!this.courseForm.name.trim() || !this.courseForm.teacher_id) {
      this.toastService.warning('Vui lòng nhập Tên lớp và Phân công giảng viên phụ trách');
      return;
    }

    this.isSubmitting.set(true);

    if (this.isEditMode() && this.currentCourseId()) {
      this.adminService.updateCourse(this.currentCourseId()!, this.courseForm).subscribe({
        next: () => {
          this.isSubmitting.set(false);
          this.toastService.success(`Cập nhật lớp học phần ${this.courseForm.name} thành công!`);
          this.closeModal();
          this.loadData();
        },
        error: (err) => {
          this.isSubmitting.set(false);
          this.toastService.error('Cập nhật thất bại: ' + (err.message || 'Lỗi server'));
        }
      });
    } else {
      this.adminService.createCourse(this.courseForm).subscribe({
        next: () => {
          this.isSubmitting.set(false);
          this.toastService.success(`Mở lớp học phần ${this.courseForm.name} thành công!`);
          this.closeModal();
          this.loadData();
        },
        error: (err) => {
          this.isSubmitting.set(false);
          this.toastService.error('Mở lớp thất bại: ' + (err.message || 'Lỗi server'));
        }
      });
    }
  }

  confirmDelete(course: Course): void {
    this.courseToDelete.set(course);
    this.showDeleteModal.set(true);
  }

  cancelDelete(): void {
    this.showDeleteModal.set(false);
    this.courseToDelete.set(null);
  }

  onExecuteDelete(): void {
    const c = this.courseToDelete();
    if (!c) return;

    this.adminService.deleteCourse(c.id).subscribe({
      next: () => {
        this.toastService.success(`Đã xóa lớp học phần ${c.name}`);
        this.cancelDelete();
        this.loadData();
      },
      error: (err) => {
        this.toastService.error('Xóa lớp thất bại: ' + (err.message || 'Lỗi server'));
      }
    });
  }

  viewClassDetail(courseId: string): void {
    this.router.navigate(['/admin/classes', courseId]);
  }
}
