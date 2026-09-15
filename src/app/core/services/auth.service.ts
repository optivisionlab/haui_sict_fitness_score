import { Injectable, computed, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, tap, map, catchError, throwError } from 'rxjs';
import { environment } from '../../../environments/environment';
import { ApiResponse, LoginRequest, LoginResponse, User, UserRole } from '../models/auth.model';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly TOKEN_KEY = 'lab_access_token';
  private readonly USER_KEY = 'lab_user_profile';

  private http = inject(HttpClient);
  private router = inject(Router);

  // Reactive State via Angular Signals
  readonly currentUser = signal<User | null>(this.getStoredUser());
  readonly isAuthenticated = computed(() => !!this.currentUser());
  readonly userRole = computed(() => this.currentUser()?.role ?? null);

  /**
   * Đăng nhập với email và mật khẩu
   */
  login(credentials: LoginRequest): Observable<LoginResponse> {
    return this.http
      .post<ApiResponse<LoginResponse>>(`${environment.apiUrl}/auth/login`, credentials)
      .pipe(
        map((response) => {
          // Backend có ResponseWrapperMiddleware bọc dữ liệu trong response.data
          const data = response?.data || (response as unknown as LoginResponse);
          return data;
        }),
        tap((data) => {
          if (data?.access_token || data?.accessToken) {
            this.setSession(data);
          }
        }),
        catchError((error) => {
          const message =
            error?.error?.detail ||
            error?.error?.message ||
            'Đăng nhập thất bại. Vui lòng kiểm tra lại tài khoản hoặc mật khẩu.';
          return throwError(() => new Error(message));
        })
      );
  }

  /**
   * Lấy thông tin người dùng hiện tại từ endpoint /auth/me
   */
  fetchCurrentUser(): Observable<User> {
    return this.http
      .get<ApiResponse<User>>(`${environment.apiUrl}/auth/me`)
      .pipe(
        map((response) => response?.data || (response as unknown as User)),
        tap((user) => {
          if (user) {
            this.currentUser.set(user);
            localStorage.setItem(this.USER_KEY, JSON.stringify(user));
          }
        })
      );
  }

  /**
   * Đăng xuất và dọn dẹp session
   */
  logout(): void {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.USER_KEY);
    this.currentUser.set(null);
    this.router.navigate(['/login']);
  }

  /**
   * Lấy token hiện tại từ localStorage
   */
  getToken(): string | null {
    return localStorage.getItem(this.TOKEN_KEY);
  }

  /**
   * Kiểm tra người dùng có một trong các roles cho phép không
   */
  hasRole(allowedRoles: UserRole[]): boolean {
    const role = this.userRole();
    if (!role) return false;
    return allowedRoles.includes(role);
  }

  /**
   * Điều hướng đến trang mặc định theo vai trò sau khi đăng nhập
   */
  redirectAfterLogin(targetRole?: UserRole): void {
    const role = targetRole || this.userRole();
    switch (role) {
      case 'teacher':
        this.router.navigate(['/teacher/classes']);
        break;
      case 'student':
        this.router.navigate(['/student/home']);
        break;
      case 'admin':
        // Nếu admin thì ưu tiên giao diện teacher hoặc quản trị
        this.router.navigate(['/teacher/classes']);
        break;
      default:
        this.router.navigate(['/']);
        break;
    }
  }

  /**
   * Lưu token và cập nhật profile
   */
  private setSession(loginData: LoginResponse): void {
    const token = loginData.accessToken || loginData.access_token;
    if (token) {
      localStorage.setItem(this.TOKEN_KEY, token);
    }
    if (loginData.user) {
      localStorage.setItem(this.USER_KEY, JSON.stringify(loginData.user));
      this.currentUser.set(loginData.user);
    } else {
      // Fallback nếu token không có user data: gọi /auth/me
      this.fetchCurrentUser().subscribe();
    }
  }

  /**
   * Khôi phục user profile từ localStorage
   */
  private getStoredUser(): User | null {
    const userStr = localStorage.getItem(this.USER_KEY);
    if (!userStr) return null;
    try {
      return JSON.parse(userStr) as User;
    } catch {
      localStorage.removeItem(this.USER_KEY);
      return null;
    }
  }
}
