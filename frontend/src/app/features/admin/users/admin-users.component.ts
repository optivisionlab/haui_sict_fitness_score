import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
  LucideUsers,
  LucideUserPlus,
  LucideSearch,
  LucideEdit3,
  LucideTrash2,
  LucideGraduationCap,
  LucideUserCheck,
  LucideShield,
  LucideCheckCircle2,
  LucideAlertCircle,
  LucideX
} from '@lucide/angular';
import { AdminService } from '@core/services/admin.service';
import { User, UserRole } from '@core/models/auth.model';
import { ToastService } from '@core/services/toast.service';

@Component({
  selector: 'app-admin-users',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    LucideUsers,
    LucideUserPlus,
    LucideSearch,
    LucideEdit3,
    LucideTrash2,
    LucideGraduationCap,
    LucideUserCheck,
    LucideShield,
    LucideCheckCircle2,
    LucideAlertCircle,
    LucideX
  ],
  templateUrl: './admin-users.component.html',
  styleUrl: './admin-users.component.scss'
})
export class AdminUsersComponent implements OnInit {
  private adminService = inject(AdminService);
  private toastService = inject(ToastService);

  users = signal<User[]>([]);
  isLoading = signal<boolean>(true);
  searchTerm = signal<string>('');
  selectedTab = signal<string>('all'); // 'all' | 'student' | 'teacher' | 'admin'

  // Modal Thêm / Sửa
  showModal = signal<boolean>(false);
  isEditMode = signal<boolean>(false);
  isSubmitting = signal<boolean>(false);
  currentUserId = signal<string | null>(null);

  userForm = {
    name: '',
    email: '',
    user_code: '',
    password: '',
    role: 'student' as UserRole,
    phone_number: ''
  };

  // Delete modal
  showDeleteModal = signal<boolean>(false);
  userToDelete = signal<User | null>(null);

  ngOnInit(): void {
    this.loadUsers();
  }

  loadUsers(): void {
    this.isLoading.set(true);
    const roleParam = this.selectedTab() === 'all' ? undefined : this.selectedTab();

    this.adminService.getUsers(roleParam, 1, 100).subscribe({
      next: (res) => {
        this.users.set(res.items || []);
        this.isLoading.set(false);
      },
      error: (err) => {
        this.isLoading.set(false);
        this.toastService.error('Không thể tải danh sách người dùng: ' + (err.message || 'Lỗi server'));
      }
    });
  }

  onTabChange(tab: string): void {
    this.selectedTab.set(tab);
    this.loadUsers();
  }

  get filteredUsers(): User[] {
    const term = this.searchTerm().trim().toLowerCase();
    if (!term) return this.users();
    return this.users().filter(u =>
      (u.name && u.name.toLowerCase().includes(term)) ||
      (u.email && u.email.toLowerCase().includes(term)) ||
      (u.user_code && u.user_code.toLowerCase().includes(term)) ||
      (u.userCode && u.userCode.toLowerCase().includes(term))
    );
  }

  openCreateModal(): void {
    this.isEditMode.set(false);
    this.currentUserId.set(null);
    this.userForm = {
      name: '',
      email: '',
      user_code: '',
      password: '',
      role: 'student',
      phone_number: ''
    };
    this.showModal.set(true);
  }

  openEditModal(user: User): void {
    this.isEditMode.set(true);
    this.currentUserId.set(user.id);
    this.userForm = {
      name: user.name || '',
      email: user.email || '',
      user_code: user.user_code || user.userCode || '',
      password: '',
      role: user.role,
      phone_number: user.phone_number || user.phoneNumber || ''
    };
    this.showModal.set(true);
  }

  closeModal(): void {
    this.showModal.set(false);
  }

  onSubmitUser(): void {
    if (!this.userForm.name.trim() || !this.userForm.email.trim()) {
      this.toastService.warning('Vui lòng nhập Họ tên và Email hợp lệ');
      return;
    }

    this.isSubmitting.set(true);

    if (this.isEditMode() && this.currentUserId()) {
      // Update
      const updateData: Partial<User> = {
        name: this.userForm.name.trim(),
        role: this.userForm.role,
        user_code: this.userForm.user_code.trim(),
        phone_number: this.userForm.phone_number.trim()
      };

      this.adminService.updateUser(this.currentUserId()!, updateData).subscribe({
        next: () => {
          this.isSubmitting.set(false);
          this.toastService.success(`Cập nhật người dùng ${this.userForm.name} thành công!`);
          this.closeModal();
          this.loadUsers();
        },
        error: (err) => {
          this.isSubmitting.set(false);
          this.toastService.error('Cập nhật thất bại: ' + (err.message || 'Lỗi server'));
        }
      });
    } else {
      // Create
      if (!this.userForm.password || this.userForm.password.length < 6) {
        this.isSubmitting.set(false);
        this.toastService.warning('Mật khẩu tối thiểu 6 ký tự');
        return;
      }

      this.adminService.createUser({
        name: this.userForm.name.trim(),
        email: this.userForm.email.trim(),
        password: this.userForm.password,
        role: this.userForm.role,
        user_code: this.userForm.user_code.trim(),
        phone_number: this.userForm.phone_number.trim()
      }).subscribe({
        next: () => {
          this.isSubmitting.set(false);
          this.toastService.success(`Tạo tài khoản ${this.userForm.name} thành công!`);
          this.closeModal();
          this.loadUsers();
        },
        error: (err) => {
          this.isSubmitting.set(false);
          this.toastService.error('Không thể tạo tài khoản: ' + (err.message || 'Email hoặc Mã tài khoản đã tồn tại'));
        }
      });
    }
  }

  confirmDelete(user: User): void {
    this.userToDelete.set(user);
    this.showDeleteModal.set(true);
  }

  cancelDelete(): void {
    this.showDeleteModal.set(false);
    this.userToDelete.set(null);
  }

  onExecuteDelete(): void {
    const user = this.userToDelete();
    if (!user) return;

    this.adminService.deleteUser(user.id).subscribe({
      next: () => {
        this.toastService.success(`Đã xóa tài khoản ${user.name}`);
        this.cancelDelete();
        this.loadUsers();
      },
      error: (err) => {
        this.toastService.error('Xóa tài khoản thất bại: ' + (err.message || 'Lỗi server'));
      }
    });
  }

  getRoleLabel(role: UserRole): string {
    switch (role) {
      case 'student': return 'Sinh viên';
      case 'teacher': return 'Giảng viên';
      case 'admin': return 'Quản trị viên';
      default: return role;
    }
  }
}
