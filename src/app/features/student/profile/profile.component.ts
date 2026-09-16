import { Component, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
  LucideUser,
  LucideMail,
  LucidePhone,
  LucideCalendar,
  LucideLock,
  LucideCamera,
  LucideKeyRound,
  LucideShieldCheck,
  LucideSave,
  LucideRefreshCw,
  LucideCheck,
  LucideAlertCircle,
  LucideGraduationCap,
  LucideMapPin,
  LucideBadgeCheck,
  LucideEye,
  LucideEyeOff,
  LucideSend,
  LucideX
} from '@lucide/angular';
import { SelectComponent } from '@shared/components';
import { StudentProfile } from './models/profile.model';

import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    SelectComponent,
    LucideUser,
    LucideMail,
    LucidePhone,
    LucideCalendar,
    LucideLock,
    LucideCamera,
    LucideKeyRound,
    LucideShieldCheck,
    LucideSave,
    LucideRefreshCw,
    LucideCheck,
    LucideAlertCircle,
    LucideGraduationCap,
    LucideMapPin,
    LucideBadgeCheck,
    LucideEye,
    LucideEyeOff,
    LucideSend,
    LucideX
  ],
  templateUrl: './profile.component.html',
  styleUrl: './profile.component.scss'
})
export class ProfileComponent {
  private authService = inject(AuthService);

  // Tabs: 'info' | 'security'
  activeTab = signal<'info' | 'security'>('info');

  // Profile data
  profile = signal<StudentProfile>(this.getInitialProfile());

  private getInitialProfile(): StudentProfile {
    const user = this.authService.currentUser();
    return {
      id: user?.id || '1',
      studentId: user?.userCode || user?.user_code || 'Chưa cập nhật',
      fullName: user?.name || 'Sinh viên',
      avatarUrl: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=250&auto=format&fit=crop&q=80',
      email: user?.email || '',
      personalEmail: '',
      phone: user?.phoneNumber || user?.phone_number || '',
      birthDate: user?.dateOfBirth || user?.date_of_birth || '',
      gender: 'male',
      idCardNumber: '',
      ethnicity: 'Kinh',
      address: '',
      hometown: '',
      faculty: 'Giáo dục Thể chất',
      major: 'Thể thao & Sức khỏe',
      classCode: '',
      cohort: '',
      status: user?.userStatus === 'active' ? 'Đang học' : (user?.userStatus || 'Đang học'),
      academicYear: '',
      gpa: 0,
      creditsEarned: 0
    };
  }

  // Editable form state
  editForm = {
    fullName: '',
    personalEmail: '',
    phone: '',
    birthDate: '',
    gender: 'male',
    address: '',
    hometown: ''
  };

  // Gender options for SelectComponent
  genderOptions = [
    { label: 'Nam', value: 'male' },
    { label: 'Nữ', value: 'female' },
    { label: 'Khác', value: 'other' }
  ];

  // Password change form
  passwordForm = {
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  };

  showCurrentPassword = signal<boolean>(false);
  showNewPassword = signal<boolean>(false);
  showConfirmPassword = signal<boolean>(false);

  // Loading & Toast state
  isSaving = signal<boolean>(false);
  isChangingPassword = signal<boolean>(false);
  toastMessage = signal<{ type: 'success' | 'error'; text: string } | null>(null);

  // Forgot password modal state
  showForgotPasswordModal = signal<boolean>(false);
  forgotEmail = signal<string>('');
  forgotStep = signal<'input' | 'sent' | 'reset'>('input');
  otpCode = signal<string>('');
  resetNewPassword = signal<string>('');
  isSendingOtp = signal<boolean>(false);

  constructor() {
    this.resetEditForm();
  }

  setTab(tab: 'info' | 'security'): void {
    this.activeTab.set(tab);
  }

  resetEditForm(): void {
    const current = this.profile();
    this.editForm = {
      fullName: current.fullName,
      personalEmail: current.personalEmail,
      phone: current.phone,
      birthDate: current.birthDate,
      gender: current.gender,
      address: current.address,
      hometown: current.hometown
    };
  }

  saveProfile(): void {
    this.isSaving.set(true);

    setTimeout(() => {
      this.profile.update((prev) => ({
        ...prev,
        fullName: this.editForm.fullName,
        personalEmail: this.editForm.personalEmail,
        phone: this.editForm.phone,
        birthDate: this.editForm.birthDate,
        gender: this.editForm.gender,
        address: this.editForm.address,
        hometown: this.editForm.hometown
      }));

      this.isSaving.set(false);
      this.showToast('success', 'Cập nhật thông tin cá nhân thành công!');
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
      this.showToast('success', 'Đổi mật khẩu thành công! Hãy dùng mật khẩu mới cho lần đăng nhập sau.');
    }, 700);
  }

  openForgotPasswordModal(): void {
    this.forgotEmail.set(this.profile().email);
    this.forgotStep.set('input');
    this.otpCode.set('');
    this.resetNewPassword.set('');
    this.showForgotPasswordModal.set(true);
  }

  closeForgotPasswordModal(): void {
    this.showForgotPasswordModal.set(false);
  }

  sendResetOtp(): void {
    if (!this.forgotEmail()) {
      this.showToast('error', 'Vui lòng nhập email.');
      return;
    }

    this.isSendingOtp.set(true);
    setTimeout(() => {
      this.isSendingOtp.set(false);
      this.forgotStep.set('sent');
      this.showToast('success', `Đã gửi mã xác nhận 6 số đến ${this.forgotEmail()}`);
    }, 800);
  }

  verifyOtpAndProceed(): void {
    if (this.otpCode().length < 4) {
      this.showToast('error', 'Vui lòng nhập đúng mã OTP gửi về email.');
      return;
    }
    this.forgotStep.set('reset');
  }

  submitNewPassword(): void {
    if (this.resetNewPassword().length < 6) {
      this.showToast('error', 'Mật khẩu mới phải có ít nhất 6 ký tự.');
      return;
    }

    this.isSendingOtp.set(true);
    setTimeout(() => {
      this.isSendingOtp.set(false);
      this.closeForgotPasswordModal();
      this.showToast('success', 'Khôi phục mật khẩu thành công! Vui lòng đăng nhập lại với mật khẩu mới.');
    }, 700);
  }

  onAvatarChange(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files[0]) {
      const file = input.files[0];
      const reader = new FileReader();
      reader.onload = () => {
        if (typeof reader.result === 'string') {
          this.profile.update((p) => ({ ...p, avatarUrl: reader.result as string }));
          this.showToast('success', 'Ảnh đại diện đã được cập nhật!');
        }
      };
      reader.readAsDataURL(file);
    }
  }

  private showToast(type: 'success' | 'error', text: string): void {
    this.toastMessage.set({ type, text });
    setTimeout(() => {
      this.toastMessage.set(null);
    }, 3500);
  }
}
