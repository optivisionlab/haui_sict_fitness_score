import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './login.component.html',
  styleUrl: './login.component.scss'
})
export class LoginComponent {
  email = signal<string>('sinhvien@haui.edu.vn');
  password = signal<string>('••••••••');
  rememberMe = signal<boolean>(true);
  showPassword = signal<boolean>(false);
  isLoading = signal<boolean>(false);
  emailError = signal<string>('');
  passwordError = signal<string>('');

  constructor(private router: Router) {}

  togglePassword(): void {
    this.showPassword.update((val) => !val);
  }

  onSubmit(event: Event): void {
    event.preventDefault();
    this.emailError.set('');
    this.passwordError.set('');

    const emailVal = this.email().trim();
    const passVal = this.password().trim();

    let hasError = false;

    if (!emailVal) {
      this.emailError.set('Vui lòng nhập Email hoặc Mã sinh viên');
      hasError = true;
    } else if (!emailVal.includes('@') && emailVal.length < 8) {
      this.emailError.set('Định dạng Email hoặc Mã sinh viên không hợp lệ');
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

    // Simulate login processing with realistic timeout
    setTimeout(() => {
      this.isLoading.set(false);
      this.router.navigate(['/student/home']);
    }, 1200);
  }
}
