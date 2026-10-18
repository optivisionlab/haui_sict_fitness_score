import { Component, signal, inject, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
  LucideUser,
  LucideAward,
  LucideShieldCheck,
  LucideLock,
  LucideSave,
  LucideCheck,
  LucideAlertCircle
} from '@lucide/angular';
import { AuthService } from '../../../core/services/auth.service';
import { UserService } from '../../../core/services/user.service';
import { ToastService } from '../../../core/services/toast.service';

@Component({
  selector: 'app-teacher-profile',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    LucideUser,
    LucideAward,
    LucideShieldCheck,
    LucideLock,
    LucideSave,
    LucideCheck
  ],
  templateUrl: './teacher-profile.component.html',
  styleUrl: './teacher-profile.component.scss'
})
export class TeacherProfileComponent {
  private authService = inject(AuthService);
  private userService = inject(UserService);
  private toastService = inject(ToastService);

  activeTab = signal<'info' | 'security'>('info');

  profile = signal<any>({});

  // Edit form model
  editForm = {
    fullName: '',
    personalEmail: '',
    phone: '',
    address: '',
    hometown: '',
    gender: 'Nam'
  };

  // Password form
  passwordForm = {
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  };

  isSaving = signal<boolean>(false);
  isChangingPassword = signal<boolean>(false);

  constructor() {
    effect(() => {
      const user = this.authService.currentUser();
      if (user) {
        this.profile.set({
          teacherId: user.userCode || user.user_code || '',
          fullName: user.name || '',
          email: user.email || '',
          personalEmail: user.personalEmail || user.personal_email || '',
          phone: user.phoneNumber || user.phone_number || '',
          gender: user.gender || 'Nam',
          birthDate: user.dateOfBirth || user.date_of_birth || '',
          address: user.address || '',
          hometown: user.hometown || '',
          status: user.userStatus === 'active' ? 'Đang công tác' : (user.userStatus || 'Đang công tác'),
          avatarUrl: 'https://ui-avatars.com/api/?name=' + encodeURIComponent(user.name || 'Giảng viên') + '&background=0D8ABC&color=fff'
        });
        this.resetEditForm();
      }
    });
  }

  setTab(tab: 'info' | 'security'): void {
    this.activeTab.set(tab);
  }

  resetEditForm(): void {
    const p = this.profile();
    this.editForm = {
      fullName: p.fullName,
      personalEmail: p.personalEmail,
      phone: p.phone,
      address: p.address,
      hometown: p.hometown,
      gender: p.gender
    };
  }

  saveProfile(): void {
    const user = this.authService.currentUser();
    if (!user) return;

    this.isSaving.set(true);
    
    const updateData = {
      name: this.editForm.fullName,
      personal_email: this.editForm.personalEmail,
      phone_number: this.editForm.phone,
      address: this.editForm.address,
      hometown: this.editForm.hometown,
      gender: this.editForm.gender
    };

    this.userService.updateProfile(user.id, updateData).subscribe({
      next: (res) => {
        this.isSaving.set(false);
        this.toastService.success('Cập nhật thông tin thành công!');
        // Trigger reload user profile in authService if needed
        this.authService.fetchCurrentUser().subscribe();
      },
      error: (err) => {
        this.isSaving.set(false);
        this.toastService.error(err.message || 'Lỗi khi cập nhật thông tin');
      }
    });
  }

  changePassword(): void {
    if (!this.passwordForm.currentPassword) {
      this.toastService.error('Vui lòng nhập mật khẩu hiện tại.');
      return;
    }
    if (this.passwordForm.newPassword.length < 6) {
      this.toastService.error('Mật khẩu mới phải có ít nhất 6 ký tự.');
      return;
    }
    if (this.passwordForm.newPassword !== this.passwordForm.confirmPassword) {
      this.toastService.error('Xác nhận mật khẩu mới không khớp.');
      return;
    }

    const user = this.authService.currentUser();
    if (!user) return;

    this.isChangingPassword.set(true);
    this.userService.updateProfile(user.id, { password: this.passwordForm.newPassword } as any).subscribe({
      next: () => {
        this.isChangingPassword.set(false);
        this.passwordForm = {
          currentPassword: '',
          newPassword: '',
          confirmPassword: ''
        };
        this.toastService.success('Đổi mật khẩu thành công!');
      },
      error: (err) => {
        this.isChangingPassword.set(false);
        this.toastService.error(err.message || 'Lỗi khi đổi mật khẩu');
      }
    });
  }
}
