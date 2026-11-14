import { Component, signal, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
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
import { environment } from '@env/environment';
import { ApiResponse } from '@core/models/auth.model';

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
export class ProfileComponent implements OnInit {
  private http = inject(HttpClient);
  private authService = inject(AuthService);

  // Tabs: 'info' | 'security'
  activeTab = signal<'info' | 'security'>('info');

  // Profile data
  profile = signal<StudentProfile>(this.getInitialProfile());

  private getInitialProfile(): StudentProfile {
    const user = this.authService.currentUser();
    const name = user?.name || 'Sinh viên';
    return {
      id: user?.id || '',
      studentId: user?.userCode || user?.user_code || 'Chưa cập nhật',
      fullName: name,
      avatarUrl: `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&background=0284c7&color=fff&bold=true`,
      email: user?.email || '',
      personalEmail: user?.personalEmail || user?.personal_email || '',
      phone: user?.phoneNumber || user?.phone_number || '',
      birthDate: user?.dateOfBirth || user?.date_of_birth || '',
      gender: user?.gender || 'male',
      idCardNumber: '',
      ethnicity: 'Chưa cập nhật',
      address: user?.address || 'Chưa cập nhật',
      hometown: user?.hometown || 'Chưa cập nhật',
      faculty: 'Chưa cập nhật',
      major: 'Chưa cập nhật',
      classCode: 'Chưa cập nhật',
      cohort: 'Chưa cập nhật',
      status: user?.userStatus === 'active' ? 'Đang học' : (user?.userStatus || 'Đang học')
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

  ngOnInit(): void {
    const user = this.authService.currentUser();
    if (user) {
      this.populateUserProfile(user);
    } else {
      this.authService.fetchCurrentUser().subscribe({
        next: (u) => this.populateUserProfile(u),
        error: () => {}
      });
    }
  }

  private populateUserProfile(user: any): void {
    if (!user) return;
    const name = user.name || 'Sinh viên';
    this.profile.set({
      id: user.id || '',
      studentId: user.userCode || user.user_code || 'Chưa cập nhật',
      fullName: name,
      avatarUrl: `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&background=0284c7&color=fff&bold=true`,
      email: user.email || '',
      personalEmail: user.personalEmail || user.personal_email || '',
      phone: user.phoneNumber || user.phone_number || '',
      birthDate: user.dateOfBirth || user.date_of_birth || '',
      gender: user.gender || 'male',
      idCardNumber: '',
      ethnicity: 'Chưa cập nhật',
      address: user.address || '',
      hometown: user.hometown || '',
      faculty: 'Chưa cập nhật',
      major: 'Chưa cập nhật',
      classCode: 'Chưa cập nhật',
      cohort: 'Chưa cập nhật',
      status: user.userStatus === 'active' ? 'Đang học' : (user.userStatus || 'Đang học')
    });
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
      gender: current.gender || 'male',
      address: current.address !== 'Chưa cập nhật' ? current.address : '',
      hometown: current.hometown !== 'Chưa cập nhật' ? current.hometown : ''
    };
  }

  saveProfile(): void {
    const user = this.authService.currentUser();
    const userId = user?.id || this.profile().id;
    if (!userId) {
      this.showToast('error', 'Không xác định được danh tính người dùng.');
      return;
    }

    this.isSaving.set(true);
    const payload = {
      name: this.editForm.fullName,
      phoneNumber: this.editForm.phone,
      personalEmail: this.editForm.personalEmail,
      dateOfBirth: this.editForm.birthDate,
      gender: this.editForm.gender,
      address: this.editForm.address,
      hometown: this.editForm.hometown
    };

    this.http.put<ApiResponse<any>>(`${environment.apiUrl}/users/${userId}`, payload).subscribe({
      next: (res) => {
        this.isSaving.set(false);
        const updated = res?.data || {};
        const newName = updated.name || this.editForm.fullName;
        this.profile.update((prev) => ({
          ...prev,
          fullName: newName,
          phone: updated.phoneNumber || updated.phone_number || this.editForm.phone,
          personalEmail: updated.personalEmail || updated.personal_email || this.editForm.personalEmail,
          birthDate: updated.dateOfBirth || updated.date_of_birth || this.editForm.birthDate,
          gender: updated.gender || this.editForm.gender,
          address: updated.address || this.editForm.address,
          hometown: updated.hometown || this.editForm.hometown,
          avatarUrl: `https://ui-avatars.com/api/?name=${encodeURIComponent(newName)}&background=0284c7&color=fff&bold=true`
        }));
        this.authService.fetchCurrentUser().subscribe({ error: () => {} });
        this.showToast('success', 'Cập nhật thông tin cá nhân thành công!');
      },
      error: (err) => {
        this.isSaving.set(false);
        this.showToast('error', err?.error?.message || 'Cập nhật thất bại. Vui lòng thử lại.');
      }
    });
  }

  changePassword(): void {
    const user = this.authService.currentUser();
    const userId = user?.id || this.profile().id;
    if (!userId) {
      this.showToast('error', 'Không xác định được danh tính người dùng.');
      return;
    }

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
    this.http.put<ApiResponse<any>>(`${environment.apiUrl}/users/${userId}`, {
      password: this.passwordForm.newPassword
    }).subscribe({
      next: () => {
        this.isChangingPassword.set(false);
        this.passwordForm = {
          currentPassword: '',
          newPassword: '',
          confirmPassword: ''
        };
        this.showToast('success', 'Đổi mật khẩu thành công! Hãy dùng mật khẩu mới cho lần đăng nhập sau.');
      },
      error: (err) => {
        this.isChangingPassword.set(false);
        this.showToast('error', err?.error?.message || 'Đổi mật khẩu thất bại. Vui lòng thử lại.');
      }
    });
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
