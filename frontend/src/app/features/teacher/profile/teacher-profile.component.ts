import { Component, signal, inject } from '@angular/core';
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
    LucideCheck,
    LucideAlertCircle
  ],
  templateUrl: './teacher-profile.component.html',
  styleUrl: './teacher-profile.component.scss'
})
export class TeacherProfileComponent {
  private authService = inject(AuthService);

  activeTab = signal<'info' | 'security'>('info');

  profile = signal(this.getInitialTeacherProfile());

  private getInitialTeacherProfile() {
    const user = this.authService.currentUser();
    return {
      teacherId: user?.userCode || user?.user_code || 'GV001',
      fullName: user?.name || 'Giảng viên',
      academicDegree: 'Giáo dục Thể chất',
      department: 'Bộ môn Giáo dục Thể chất',
      university: 'Trường Đại học Công nghiệp Hà Nội (HaUI)',
      email: user?.email || '',
      personalEmail: '',
      phone: user?.phoneNumber || user?.phone_number || '',
      gender: 'Nam',
      birthDate: user?.dateOfBirth || user?.date_of_birth || '',
      address: '',
      specialties: 'Giáo dục thể chất, Thể dục thể thao học đường',
      status: user?.userStatus === 'active' ? 'Đang công tác' : (user?.userStatus || 'Đang công tác'),
      teachingClassesCount: 0,
      totalStudentsCount: 0,
      avatarUrl: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=250&auto=format&fit=crop&q=80'
    };
  }

  // Edit form model
  editForm = {
    fullName: '',
    personalEmail: '',
    phone: '',
    address: '',
    specialties: ''
  };

  // Password form
  passwordForm = {
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  };

  isSaving = signal<boolean>(false);
  isChangingPassword = signal<boolean>(false);
  toastMessage = signal<{ type: 'success' | 'error'; text: string } | null>(null);

  constructor() {
    this.resetEditForm();
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
      specialties: p.specialties
    };
  }

  saveProfile(): void {
    this.isSaving.set(true);
    setTimeout(() => {
      this.profile.update(prev => ({
        ...prev,
        fullName: this.editForm.fullName,
        personalEmail: this.editForm.personalEmail,
        phone: this.editForm.phone,
        address: this.editForm.address,
        specialties: this.editForm.specialties
      }));
      this.isSaving.set(false);
      this.showToast('success', 'Cập nhật thông tin giảng viên thành công!');
    }, 600);
  }

  changePassword(): void {
    if (!this.passwordForm.currentPassword) {
      this.showToast('error', 'Vui lòng nhập mật khẩu hiện tại.');
      return;
    }
    if (this.passwordForm.newPassword.length < 6) {
      this.showToast('error', 'Mật khẩu mới phải có ít nhất 6 ký tự.');
      return;
    }
    if (this.passwordForm.newPassword !== this.passwordForm.confirmPassword) {
      this.showToast('error', 'Xác nhận mật khẩu mới không khớp.');
      return;
    }

    this.isChangingPassword.set(true);
    setTimeout(() => {
      this.isChangingPassword.set(false);
      this.passwordForm = {
        currentPassword: '',
        newPassword: '',
        confirmPassword: ''
      };
      this.showToast('success', 'Đổi mật khẩu tài khoản Giảng viên thành công!');
    }, 700);
  }

  private showToast(type: 'success' | 'error', text: string): void {
    this.toastMessage.set({ type, text });
    setTimeout(() => {
      this.toastMessage.set(null);
    }, 3500);
  }
}
