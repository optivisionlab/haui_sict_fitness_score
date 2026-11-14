import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';
import { ToastService } from '../../../core/services/toast.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './login.component.html',
  styleUrl: './login.component.scss'
})
export class LoginComponent {
  private authService = inject(AuthService);
  private toastService = inject(ToastService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);

  email = signal<string>('');
  password = signal<string>('');
  rememberMe = signal<boolean>(false);
  showPassword = signal<boolean>(false);
  isLoading = signal<boolean>(false);
  emailError = signal<string>('');
  passwordError = signal<string>('');
  generalError = signal<string>('');

  togglePassword(): void {
    this.showPassword.update((val) => !val);
  }

  onSubmit(event: Event): void {
    event.preventDefault();
    this.emailError.set('');
    this.passwordError.set('');
    this.generalError.set('');

    const emailVal = this.email().trim();
    const passVal = this.password().trim();

    let hasError = false;

    if (!emailVal) {
      this.emailError.set('Vui lòng nhập Email hoặc Mã tài khoản');
      hasError = true;
    } else if (!emailVal.includes('@') && emailVal.length < 5) {
      this.emailError.set('Định dạng Email hoặc Mã tài khoản không hợp lệ');
      hasError = true;
    }

    if (!passVal) {
      this.passwordError.set('Vui lòng nhập mật khẩu');
      hasError = true;
    } else if (passVal.length < 6) {
      this.passwordError.set('Mật khẩu tối thiểu 6 ký tự');
      hasError = true;
    }

    if (hasError) return;

    this.isLoading.set(true);

    this.authService.login({ email: emailVal, password: passVal }).subscribe({
      next: (response) => {
        this.isLoading.set(false);
        const userName = response.user?.name || '';
        const roleLabel = response.user?.role === 'teacher' ? 'Giảng viên' : (response.user?.role === 'admin' ? 'Quản trị viên' : 'Sinh viên');

        // Bắn thông báo Toast để khi vào dashboard sẽ hiển thị nổi bật ở góc màn hình
        this.toastService.success(
          `Chào mừng ${roleLabel} ${userName} quay trở lại hệ thống!`,
          'Đăng nhập thành công'
        );

        const returnUrl = this.route.snapshot.queryParams['returnUrl'];
        if (returnUrl && returnUrl.startsWith('/')) {
          this.router.navigateByUrl(returnUrl);
        } else {
          this.authService.redirectAfterLogin(response.user?.role);
        }
      },
      error: (err) => {
        this.isLoading.set(false);
        this.generalError.set(err.message || 'Đăng nhập thất bại. Vui lòng thử lại.');
      }
    });
  }
}
